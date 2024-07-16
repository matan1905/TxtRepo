from .base import DslInstruction
from difflib import SequenceMatcher

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

        # Find the best match for the patch in the original file
        start_index = self.find_best_patch_location(lines, patch)

        if start_index == -1:
            raise ValueError("Suitable patch location not found in the file")

        # Apply the patch
        result = lines[:start_index]
        i = start_index
        for op, line in patch:
            if op == ' ':
                if i < len(lines) and self.lines_similar(lines[i], line):
                    result.append(lines[i])
                    i += 1
                else:
                    result.append(line)
            elif op == '-':
                if i < len(lines) and self.lines_similar(lines[i], line):
                    i += 1
            elif op == '+':
                result.append(line)
        result.extend(lines[i:])

        return result, "Patch applied successfully"

    def find_best_patch_location(self, lines, patch):
        context_lines = [p[1] for p in patch if p[0] in (' ', '-')]
        best_score = 0
        best_index = -1

        for i in range(len(lines) - len(context_lines) + 1):
            score = sum(self.lines_similar(lines[i + j], line) for j, line in enumerate(context_lines))
            if score > best_score:
                best_score = score
                best_index = i

        # Set a threshold for minimum acceptable score
        if best_score < len(context_lines) * 0.7:  # 70% similarity required
            return -1
        return best_index

    def lines_similar(self, line1, line2):
        return SequenceMatcher(None, line1.strip(), line2.strip()).ratio() > 0.8

    @classmethod
    def parse(cls, args):
        return cls()