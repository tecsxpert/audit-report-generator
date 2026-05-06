def format_code(code: str) -> str:
    """Format the generated code."""
    # Simple formatting: add indentation
    lines = code.split('\n')
    formatted = []
    indent_level = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except:', 'finally:')):
            formatted.append('    ' * indent_level + stripped)
            if not stripped.endswith(':'):
                indent_level += 1
        elif stripped.startswith(('return ', 'break', 'continue', 'pass')):
            formatted.append('    ' * indent_level + stripped)
            indent_level = max(0, indent_level - 1)
        else:
            formatted.append('    ' * indent_level + stripped)
    return '\n'.join(formatted)

def validate_prompt(prompt: str) -> bool:
    """Validate the user prompt."""
    return len(prompt.strip()) > 0 and len(prompt) < 1000