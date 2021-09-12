import socket
import argparse
import sys
import signal
import threading
from threading import Thread

HEADER = """Content-Disposition: attachment; filename="{}"\r\nContent-Type: 
application/octet-stream\r\nContent-Length: {}\r\n\r\n """
ACCIO = b"accio\r\n"
CHUNK = 4096
TIMEOUT = 10
FILE_DIR = ''
not_stopped = True


def handler(signum, frame):
    global not_stopped
    not_stopped = False


class Client(threading.Thread):
    MAX_LINE = 1024

    def __init__(self, conn, id):
        threading.Thread.__init__(self)
        self._id = id
        self._sock = conn
        self._sock.settimeout(TIMEOUT)
        self._recv_buffer = b''
        self._pos = 0

    def run(self):
        try:
            self._send_accio()
        except socket.timeout:
            sys.stderr.write(f"ERROR: timeout for not able to send to client within {TIMEOUT} seconds.\n")
            self._close()
            return
        try:
            file_size = self._recv_header()
        except socket.timeout:
            sys.stderr.write(f"ERROR: timeout for not able to receive from client within {TIMEOUT} seconds.\n")
            self._close()
            return
        with open(f'{FILE_DIR}/{self._id}.file', 'wb') as f:
            recv_size = 0
            while recv_size < file_size:
                try:
                    data = self._recv_data(CHUNK)
                except socket.timeout:
                    f.truncate(0)  # partial content from client must be discarded
                    f.write(
                        f"ERROR: timeout for not able to receive from client within {TIMEOUT} seconds.".encode('utf8'))
                    self._close()
                    return
                if data == b'':
                    break
                f.write(data)
                recv_size += len(data)
            if recv_size < file_size:
                f.truncate(0)  # partial content from client must be discarded

        self._close()

    def _send_accio(self):
        self._send(ACCIO)

    def _recv_header(self):
        self._readline()
        self._readline()
        line = self._readline()
        file_size = int(line.strip().split()[1])
        self._readline()
        return file_size

    def _recv_data(self, chunk_size):
        chunk = []
        i = 0
        while i < chunk_size:
            b = self._get_byte()
            if b == b'':
                break
            chunk.append(b)
            i += 1
        return b''.join(chunk)

    def _close(self):
        self._sock.close()

    def _readline(self):
        line = []
        i = 0
        while i < Client.MAX_LINE:
            b = self._get_byte()
            if b == b'':
                break
            line.append(b)
            if b == b'\n':
                break
            i += 1
        return b''.join(line)

    def _get_byte(self):
        if self._pos >= len(self._recv_buffer):
            self._recv(CHUNK)
        if self._recv_buffer == b'':
            return b''
        self._pos += 1
        return self._recv_buffer[self._pos - 1: self._pos]

    def _send(self, data):
        if isinstance(data, str):
            data = data.encode('utf8')
        assert isinstance(data, bytes)
        totalsent = 0

        while totalsent < len(data):
            sent = self._sock.send(data[totalsent:])
            if sent == 0:
                sys.stderr.write("ERROR: client has closed\n")
                self._sock._close()
            totalsent = totalsent + sent

    def _recv(self, length):
        chunks = []
        bytes_recd = 0
        while bytes_recd < length:
            chunk = self._sock.recv(min(length - bytes_recd, CHUNK))
            if chunk == b'':
                break
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        self._recv_buffer = b''.join(chunks)
        self._pos = 0


class Server:
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.sock.bind(('0.0.0.0', port))
        except OverflowError:
            sys.stderr.write("Error: port must be 0-65535\n")
            sys.exit(1)
        self.sock.listen(20)
        print("Starting server")

    def run(self):
        id = 1
        while not_stopped:
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            Client(conn, id).start()
            id += 1
        print("Closing server")
        self.sock.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="port number on which server will listen on connections", type=int)
    parser.add_argument("file_dir", help="directory name where to save the received files")
    args = parser.parse_args()
    return args.port, args.file_dir


def main():
    global FILE_DIR
    port, FILE_DIR = parse_args()
    server = Server(port)
    signal.signal(signal.SIGINT, handler)
    server.run()


if __name__ == '__main__':
    main()
