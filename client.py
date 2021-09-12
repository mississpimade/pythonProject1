import socket
import argparse
import os
import sys

HEADER = """Content-Disposition: attachment; filename="{}"\r\nContent-Type: 
application/octet-stream\r\nContent-Length: {}\r\n\r\n """
ACCIO = b"accio\r\n"
CHUNK = 4096
TIMEOUT = 10


class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(TIMEOUT)

    def connect(self, hostname, port):
        try:
            self.sock.connect((hostname, port))
        except socket.timeout:
            sys.stderr.write(f"ERROR: timeout to connect to server within {TIMEOUT} seconds\n")
            sys.exit(1)
        except (OSError, OverflowError):
            sys.stderr.write("ERROR: incorrect hostname or port number\n")
            sys.exit(1)

    def send(self, data):
        if isinstance(data, str):
            data = data.encode('utf8')
        else:
            pass
        assert isinstance(data, bytes)
        totalsent = 0

        while totalsent < len(data):
            try:
                sent = self.sock.send(data[totalsent:])
            except socket.timeout:
                sys.stderr.write(f"ERROR: timeout for not able to send to server within {TIMEOUT} seconds.\n")
                sys.exit(1)
            if sent == 0:
                sys.stderr.write("ERROR: server has closed\n")
                sys.exit(1)
            totalsent = totalsent + sent

    def recv(self, length):
        chunks = []
        bytes_recd = 0
        while bytes_recd < length:
            try:
                chunk = self.sock.recv(min(length - bytes_recd, CHUNK))
            except socket.timeout:
                sys.stderr.write(f"ERROR: timeout for not able to receive from server within {TIMEOUT} seconds.\n")
                sys.exit(1)
            if chunk == b'':
                break
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return b''.join(chunks)

    def close(self):
        self.sock.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname", help="hostname or IP address of the server to connect")
    parser.add_argument("port", help="port number of the server to connect", type=int)
    parser.add_argument("filename",
                        help="name of the file to transfer to the server after the connection is established")
    args = parser.parse_args()
    return args.hostname, args.port, args.filename


def send_header(client, filename):
    client.send(HEADER.format(filename, os.stat(filename).st_size))


def send_data(client, filename):
    with open(filename, 'rb') as f:
        while True:
            data = f.read(CHUNK)
            if data:
                client.send(data)
            else:
                break


def main():
    hostname, port, filename = parse_args()
    client = Client()
    client.connect(hostname, port)
    received_msg = client.recv(len(ACCIO))
    assert received_msg == ACCIO
    send_header(client, filename)
    send_data(client, filename)
    client.close()


if __name__ == '__main__':
    main()
