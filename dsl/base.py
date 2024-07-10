from abc import ABC, abstractmethod

class DslInstruction(ABC):
    @abstractmethod
    def apply(self, file_path, content, lines):
        pass

    @classmethod
    @abstractmethod
    def parse(cls, args):
        pass