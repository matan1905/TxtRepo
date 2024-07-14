from .base import DslInstruction

class PatchInstruction(DslInstruction):
    def __init__(self, old_content, new_content):
        self.old_content = old_content
        self.new_content = new_content

    def apply(self, file_path, content, lines):
        file_content = ''.join(lines)
        patched_content = file_content.replace(self.old_content, self.new_content)
        new_lines = patched_content.splitlines(keepends=True)
        return new_lines, f"Applied patch to {file_path}"

    @classmethod
    def parse(cls, args):
        old_content, new_content = args.split('+++', 1)
        old_content = old_content.strip().replace('---', '', 1).strip()
        new_content = new_content.strip()
        return cls(old_content, new_content)