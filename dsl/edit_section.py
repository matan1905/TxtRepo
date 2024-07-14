from .base import DslInstruction


class EditSectionInstruction(DslInstruction):
    """
    Patches parts of a file.
    The format is:
    # File path/to/file::patch
    def addBias(x):
    ---    bias = 1
    +++    bias = 5
        return bias + x
    # EndFile path/to/file
    """
    def apply(self, file_path, content, lines):
        patch_lines = content.split('\n')

        patch = []
        for line in patch_lines:
            if line.startswith('---'):
                patch.append(('-', line[3:]))
            elif line.startswith('+++'):
                patch.append(('+', line[3:]))
            else:
                patch.append((' ', line))

        # Step 3: Find the patch location in the original file
        start_index = -1
        for i in range(len(lines) - len(patch) + 1):
            if all(lines[i + j].strip() == p[1].strip() for j, p in enumerate(patch) if p[0] in (' ', '-')):
                start_index = i
                break

        if start_index == -1:
            raise ValueError("Patch location not found in the file")

        # Step 4: Apply the patch
        result = lines[:start_index]
        i = start_index
        for op, line in patch:
            if op == ' ':
                result.append(line)
                i += 1
            elif op == '-':
                i += 1
            elif op == '+':
                result.append(line)
        result.extend(lines[i:])

        return result







    @classmethod
    def parse(cls, args):
        return cls()
