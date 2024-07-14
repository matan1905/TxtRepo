from .patch import PatchInstruction
from .delete_file import DeleteFileInstruction
from .inject_at_line import InjectAtLineInstruction

class DslInstructionFactory:
    @staticmethod
    def create(dsl_string):
        if not dsl_string:
            return None

        instructions = {
            'delete-file': DeleteFileInstruction,
'patch': PatchInstruction,
            'inject-at-line': InjectAtLineInstruction
        }

        if ':' in dsl_string:
            command, args = dsl_string.split(':', 1)
        else:
            command, args = dsl_string, ''

        if command in instructions:
            return instructions[command].parse(args)

        return None