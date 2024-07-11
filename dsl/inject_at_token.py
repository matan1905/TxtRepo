from .base import DslInstruction, Token

class InjectAtTokenInstruction(DslInstruction):
    def __init__(self, token_id):
        self.token_id = token_id

    def apply(self, file_path, content, tokens):
        for i, token in enumerate(tokens):
            if token.token_type == 'id' and token.content == self.token_id:
                new_token = Token(content, 'content')
                tokens.insert(i + 1, new_token)
                return tokens, f"Injected content after token {self.token_id}"
        return tokens, f"Token {self.token_id} not found"

    @classmethod
    def parse(cls, arg):
        return cls(arg)