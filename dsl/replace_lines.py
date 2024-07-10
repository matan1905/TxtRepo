from .base import DslInstruction

class ReplaceLinesInstruction(DslInstruction):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def apply(self, file_path, content, lines):
        lines[self.start-1:self.end] = [content + '\n']
        return True, f"Replaced lines {self.start}-{self.end}"

    @classmethod
    def parse(cls, args):
        start, end = map(int, args.split('-'))
        return cls(start, end)