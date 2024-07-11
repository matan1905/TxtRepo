from .delete_file import DeleteFileInstruction
from .delete_tokens import DeleteTokensInstruction
from .replace_tokens import ReplaceTokensInstruction
from .inject_at_token import InjectAtTokenInstruction

class DslInstructionFactory:
    @staticmethod
    def create(dsl_string):
        if not dsl_string:
            return None

        instructions = {
            'delete-file': DeleteFileInstruction,
            'delete-tokens': DeleteTokensInstruction,
            'replace-tokens': ReplaceTokensInstruction,
            'inject-at-token': InjectAtTokenInstruction
        }

        if ':' in dsl_string:
            command, args = dsl_string.split(':', 1)
        else:
            command, args = dsl_string, ''

        if command in instructions:
            return instructions[command].parse(args)

        return None