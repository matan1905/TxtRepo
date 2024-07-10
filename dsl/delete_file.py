from .base import DslInstruction

class DeleteFileInstruction(DslInstruction):
    def apply(self, file_path, content, lines):
        if file_path.exists():
            file_path.unlink()
            return True, "File deleted"
        return False, "File does not exist"

    @classmethod
    def parse(cls, args):
        return cls()