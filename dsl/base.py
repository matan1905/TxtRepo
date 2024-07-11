from abc import ABC, abstractmethod

class Token:
    def __init__(self, content, token_type):
        self.content = content
        self.token_type = token_type

class DslInstruction(ABC):
    @abstractmethod
    def apply(self, file_path, content, tokens):
        pass

    @classmethod
    @abstractmethod
    def parse(cls, args):
        pass