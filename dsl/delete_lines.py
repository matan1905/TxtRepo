from .base import DslInstruction

class DeleteLinesInstruction(DslInstruction):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def apply(self, file_path, content, lines):
        del lines[self.start-1:self.end]
        return True, f"Deleted lines {self.start}-{self.end}"

    @classmethod
    def parse(cls, args):
        start, end = map(int, args.split('-'))
        return cls(start, end)