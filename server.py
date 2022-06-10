import os
import queue
import re
import socketserver
from functools import cached_property
from typing import Callable, Dict, Tuple

from common import *

FILES_PATH = os.path.join(os.path.dirname(__file__), 'files')


class Server(MessageHandler):
    def __init__(self, message_sender: Callable[[Message], None]):
        self._message_sender = message_sender
    
    @cached_property
    def message_queue(self):
        return queue.SimpleQueue()

    def _send_only(self, msg: Message) -> None:
        self._message_sender(msg)

    def _receive_only(self) -> Message:
        try:
            return self.message_queue.get(timeout=TIMEOUT)
        except queue.Empty:
            raise TimeoutError(f"Timeout of {TIMEOUT}s expired.")

    def send_error(self, error: str) -> None:
        print(f'Sent ERROR: "{error}"')
        return super().send_error(error)

    def handle_command(self):
        handlers = {
            Command.GET: self.handle_get,
            Command.LIST: self.handle_list,
            Command.PUT: self.handle_put,
        }
        try:
            cmd = self.receive()
            handlers[cmd.text]()
        except MessageHandler.Error as e:
            self.send_error(str(e))
        except Exception as e:
            self.send_error(f'Internal error: {e}')

    def ensure_files_dir(self) -> None:
        os.makedirs(FILES_PATH, exist_ok=True)

    def is_filename_valid(self, name: str) -> bool:
        return re.match(r'^[a-zA-Z0-9.\-_ ]+$', name) is not None

    def handle_get(self):
        name = self.receive().text
        if not self.is_filename_valid(name):
            return self.send_error(f'Invalid filename "{name}".')
        self.ensure_files_dir()
        fn = os.path.join(FILES_PATH, name)
        if not os.path.isfile(fn):
            return self.send_error(f'File "{name}" does not exist')
        self.send_file(fn)
        print(f'File "{name}" sent successfully.')

    def handle_put(self):
        name = self.receive().text
        if not self.is_filename_valid(name):
            return self.send_error(f'Invalid filename "{name}".')
        self.ensure_files_dir()
        fn = os.path.join(FILES_PATH, name)
        self.receive_file(fn)
        print(f'File "{name}" received successfully.')

    def handle_list(self):
        self.ensure_files_dir()
        self.send(Message.from_text('\n'.join(os.listdir(FILES_PATH))))
        print('File list sent successfully.')


class RequestHandler(socketserver.BaseRequestHandler):
    _servers: Dict[Tuple[str, int], Server] = {}

    def handle(self) -> None:
        packet, self.socket = self.request
        msg = decode_message(packet)

        if msg.is_command:
            RequestHandler._servers[self.client_address] = Server(self.send_message)
        elif self.client_address not in RequestHandler._servers:
            return Server(self.send_message).send_error('No command specified')
        server = RequestHandler._servers[self.client_address]
        server.message_queue.put_nowait(msg)
        if msg.is_command:
            server.handle_command()
            del RequestHandler._servers[self.client_address]
    
    def send_message(self, msg: Message) -> None:
        self.socket.sendto(encode_message(msg), self.client_address)


with socketserver.ThreadingUDPServer(SERVER_ADDR, RequestHandler) as server:
    try:
        server.daemon_threads = True
        server.serve_forever()
    except KeyboardInterrupt:
        print('Closing server...')
