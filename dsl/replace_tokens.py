from .base import DslInstruction, Token

class ReplaceTokensInstruction(DslInstruction):
    def __init__(self, start_id, end_id):
        self.start_id = start_id
        self.end_id = end_id

    def apply(self, file_path, content, tokens):
        start_index = None
        end_index = None
        for i, token in enumerate(tokens):
            if token.token_type == 'id':
                if token.content == self.start_id:
                    start_index = i
                elif token.content == self.end_id:
                    end_index = i
                    break
        
        if start_index is not None and end_index is not None:
            new_token = Token(content, 'content')
            tokens[start_index:end_index+1] = [new_token]
            return tokens, f"Replaced tokens from {self.start_id} to {self.end_id}"
        return tokens, f"Tokens {self.start_id} and/or {self.end_id} not found"

    @classmethod
    def parse(cls, args):
        start_id, end_id = args.split('-')
        return cls(start_id, end_id)