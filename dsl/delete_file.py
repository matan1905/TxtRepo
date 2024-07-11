from .base import DslInstruction

class DeleteFileInstruction(DslInstruction):
    def apply(self, file_path, content, tokens):
        if file_path.exists():
            file_path.unlink()
            return None, "File deleted"
        return None, "File does not exist"

    @classmethod
    def parse(cls, args):
        return cls()