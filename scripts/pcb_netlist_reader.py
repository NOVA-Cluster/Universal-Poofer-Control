"""Small data-only KiCad S-expression reader (Python3.9+; no external skill dependency)."""
import json
import re
from pathlib import Path

TOKEN=re.compile(r'\s*(?:#[^\n]*(?:\n|$)|\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+)')
BRACES={'dblquote':'"','quote':"'",'lt':'<','gt':'>','backslash':'\\','slash':'/','bar':'|','colon':':','space':' ','amp':'&','tab':'\t','newline':'\n','return':'\r','brace':'{'}

def decode(value):
    return re.sub(r'\{([a-z]+)\}',lambda m:BRACES.get(m.group(1),m.group(0)),value)

def parse(text):
    stack=[]
    result=None
    offset=0
    while offset<len(text):
        match=TOKEN.match(text,offset)
        if not match:
            if not text[offset:].strip():break
            raise ValueError('Malformed KiCad token at character%d'%offset)
        token=match.group(0).strip();offset=match.end()
        if token.startswith('#'):continue
        if token=='(':
            node=[]
            if stack:stack[-1].append(node)
            elif result is not None:raise ValueError('Multiple root expressions')
            else:result=node
            stack.append(node)
        elif token==')':
            if not stack:raise ValueError('Unexpected closing parenthesis')
            stack.pop()
        else:
            if not stack:raise ValueError('Atom outside root expression')
            stack[-1].append(decode(json.loads(token,strict=False) if token.startswith('"') else token))
    if stack:raise ValueError('Unterminated KiCad expression')
    if result is None:raise ValueError('Empty KiCad document')
    return result

def parse_file(path):return parse(Path(path).read_text(encoding='utf-8'))
def find_all(node,key):return [child for child in node if isinstance(child,list) and child and child[0]==key] if isinstance(node,list) else []
def find_first(node,key):return next(iter(find_all(node,key)),None)
