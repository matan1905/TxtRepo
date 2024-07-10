from .base import DslInstruction
import os

class DeleteFileInstruction(DslInstruction):
    def apply(self, file_path, content, lines):
        if os.path.exists(file_path):
            os.remove(file_path)
            return None, "File deleted"
        return lines, "File does not exist"

    @classmethod
    def parse(cls, args):
        return cls()