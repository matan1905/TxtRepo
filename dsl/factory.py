from .delete_file import DeleteFileInstruction
from .inject_at_line import InjectAtLineInstruction
from .edit_section import  EditSectionInstruction

class DslInstructionFactory:
    @staticmethod
    def create(dsl_string):
        if not dsl_string:
            return None

        instructions = {
            'delete-file': DeleteFileInstruction,
            'inject-at-line': InjectAtLineInstruction,
            'edit-section': EditSectionInstruction
        }

        if ':' in dsl_string:
            command, args = dsl_string.split(':', 1)
        else:
            command, args = dsl_string, ''

        if command in instructions:
            return instructions[command].parse(args)

        return None