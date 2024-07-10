from typing import Dict, Any, Callable
import re

class DSLRegistry:
    def __init__(self):
        self.commands = {}

    def register(self, name: str):
        def decorator(func: Callable):
            self.commands[name] = func
            return func
        return decorator

    def execute(self, command: str, content: str, file_path: str) -> Dict[str, Any]:
        for name, func in self.commands.items():
            if command.startswith(name):
                args = command[len(name):].strip()
                return func(content, file_path, args)
        raise ValueError(f"Unknown DSL command: {command}")

dsl_registry = DSLRegistry()

@dsl_registry.register("delete")
def delete_file(content: str, file_path: str, args: str) -> Dict[str, Any]:
    return {"delete": True}

@dsl_registry.register("injectAtLine")
def inject_at_line(content: str, file_path: str, args: str) -> Dict[str, Any]:
    line_number = int(args)
    return {"inject_at_line": line_number}

def parse_dsl(dsl_string: str, content: str, file_path: str) -> Dict[str, Any]:
    if not dsl_string:
        return {}

    commands = re.split(r'\s*::\s*', dsl_string)
    result = {}
    for command in commands:
        result.update(dsl_registry.execute(command, content, file_path))
    return result