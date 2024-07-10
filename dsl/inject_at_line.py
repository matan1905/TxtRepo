from .base import DslInstruction

class InjectAtLineInstruction(DslInstruction):
    def __init__(self, line_number):
        self.line_number = line_number

    def apply(self, file_path, content, lines):
        lines.insert(self.line_number - 1, content + '\n')
        return True, f"Injected content at line {self.line_number}"

    @classmethod
    def parse(cls, arg):
        return cls(int(arg))