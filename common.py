import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from typing import List, Optional

SERVER_ADDR = ('127.0.0.1', 12345)

TIMEOUT = 5
HEADER_SIZE = 1
MAX_RECV_SIZE = 2**16
MAX_BLOCK_SIZE = 2**10 - HEADER_SIZE
assert MAX_RECV_SIZE >= MAX_BLOCK_SIZE + HEADER_SIZE

_ENCODE_MORE_BLOCKS = 1<<0
_ENCODE_COMMAND = 1<<1
_ENCODE_ERROR = 1<<2

@dataclass
class Message:
    content: bytes
    is_command: bool = False
    is_error: bool = False
    has_more: bool = False

    @property
    def text(self):
        return self.content.decode()

    @staticmethod
    def from_text(text: str, **kwargs) -> "Message":
        return Message(content=text.encode(), **kwargs)

    @staticmethod
    def command(command: str) -> "Message":
        return Message.from_text(command, is_command=True)

    @staticmethod
    def error(error: str) -> "Message":
        return Message.from_text(error, is_error=True)

class MessageHandler(ABC):
    @abstractmethod
    def _send_only(self, msg: Message) -> None:
        pass

    @abstractmethod
    def _receive_only(self) -> Message:
        pass

    class Error(Exception): pass

    def _ensure_receive_ok_message(self):
        ok = self._receive_only()
        if not is_ok_message(ok):
            raise MessageHandler.Error("Unexpected answer")

    def _receive_one(self) -> Message:
        m = self._receive_only()
        self._send_only(OK_MESSAGE)
        return m

    def send(self, msg: Message) -> None:
        for m in split_message(msg):
            self._send_only(m)
            self._ensure_receive_ok_message()

    def send_error(self, error: str) -> None:
        self._send_only(Message.error(error))
    
    def receive(self) -> Message:
        more_blocks = True
        is_command = False
        is_error = False
        content = bytearray()
        while more_blocks:
            msg = self._receive_one()
            content.extend(msg.content)
            more_blocks = msg.has_more
            is_command = msg.is_command
            is_error = msg.is_error
        return Message(content=content, is_command=is_command, is_error=is_error)
        
    def receive_file(self, output_path: str) -> None:
        h = sha256()
        try:
            with tempfile.NamedTemporaryFile('wb', delete=False) as file:
                while True:
                    m = self._receive_one()
                    h.update(m.content)
                    file.write(m.content)
                    if not m.has_more:
                        break
            remote_hash = self.receive().content
            if h.digest() != remote_hash:
                raise MessageHandler.Error('Hash mismatch. Please try again!')
        except Exception as e:
            os.remove(file.name)
            raise e

        os.replace(file.name, output_path)
        self.send(OK_MESSAGE)

    def send_file(self, input_path: str) -> None:
        h = sha256()
        with open(input_path, 'rb') as file:
            while True:
                chunk = file.read(MAX_BLOCK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
                self.send(Message(chunk, has_more=True))
        self.send(Message(b'', has_more=False))
        checksum = h.digest()
        self.send(Message(checksum))
        if not is_ok_message(self.receive()):
            raise MessageHandler.Error('Hash mismatch. Please try again!')

class Command:
    LIST = 'L'
    GET = 'G'
    PUT = 'P'


OK_MESSAGE = Message(b"Y", is_command=False, is_error=False)

def is_ok_message(msg: Optional[Message]) -> bool:
    return msg is not None and msg.content == OK_MESSAGE.content

def encode_message(msg: Message) -> bytes:
    header = 0
    if msg.is_command:
        header |= _ENCODE_COMMAND
    if msg.is_error:
        header |= _ENCODE_ERROR
    if msg.has_more:
        header |= _ENCODE_MORE_BLOCKS
    return bytes([header]) + msg.content

def split_message(msg: Message) -> List[Message]:
    if len(msg.content) <= MAX_BLOCK_SIZE:
        return [msg]

    blocks = [msg.content[i:i+MAX_BLOCK_SIZE] for i in range(0, len(msg.content), MAX_BLOCK_SIZE)]
    messages = [Message(b, is_command=msg.is_command, is_error=msg.is_error, has_more=True) for b in blocks]
    messages[-1].has_more = msg.has_more
    return messages

def decode_message(buff: bytes) -> Message:
    header = buff[0]
    is_command = header & _ENCODE_COMMAND != 0
    is_error = header & _ENCODE_ERROR != 0
    more_blocks = header & _ENCODE_MORE_BLOCKS != 0
    return Message(content=buff[1:], is_command=is_command, is_error=is_error, has_more=more_blocks)
