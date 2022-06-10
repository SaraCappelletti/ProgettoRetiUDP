import argparse
import socket
import sys

from common import *


def error_and_exit(msg: str):
    print(f'[ERROR]: {msg}', file=sys.stderr)
    exit(1)


class Client(MessageHandler):
    def __init__(self, addr):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(TIMEOUT)
        self.addr = addr

    def _send_only(self, msg: Message) -> None:
        self.sock.sendto(encode_message(msg), self.addr)

    def _receive_only(self) -> Message:
        m = decode_message(self.sock.recv(MAX_RECV_SIZE))
        if m.is_error:
            error_and_exit(m.text)
        return m

    def handle_get(self, name: str, output_path: str):
        self.send(Message.command(Command.GET))
        self.send(Message.from_text(name))
        self.receive_file(output_path)
        print(f'File "{name}" received successfully in "{output_path}".')

    def handle_put(self, name: str, input_path: str):
        self.send(Message.command(Command.PUT))
        self.send(Message.from_text(name))
        self.send_file(input_path)
        print(f'File "{name}" sent successfully.')

    def handle_list(self):
        self.send(Message.command(Command.LIST))
        list = self.receive()
        print('Available files in the server:')
        for l in list.text.splitlines():
            print(f'• {l}')


parser = argparse.ArgumentParser('UDP Client')
subparser = parser.add_subparsers(required=True, dest='command')

get_parser = subparser.add_parser('get', help='Download a file from the server.')
get_parser.add_argument('name', type=str, help='The remote file name.')
get_parser.add_argument('out_file', type=str, help='The path in which to save the file.')

put_parser = subparser.add_parser('put', help='Upload a file to the server.')
put_parser.add_argument('name', type=str, help='The remote file name.')
put_parser.add_argument('in_file', type=str, help='The path of the file to send.')

list_parser = subparser.add_parser('list', help='Show a list of the file available in the server.')

args = parser.parse_args()
client = Client(SERVER_ADDR)
try:
    if args.command == 'get':
        client.handle_get(args.name, args.out_file)
    elif args.command == 'put':
        client.handle_put(args.name, args.in_file)
    elif args.command == 'list':
        client.handle_list()
    else:
        parser.print_usage()
except TimeoutError:
    error_and_exit('The server stopped responding :(')
except KeyboardInterrupt:
    error_and_exit(f'Command "{args.command}" interrupted by the user.')
except MessageHandler.Error as e:
    error_and_exit(str(e))
