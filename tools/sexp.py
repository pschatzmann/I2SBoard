"""Minimal KiCad s-expression parser/writer."""
import re

TOK = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')

class Str(str):
    """A quoted string."""

def parse(text):
    pos = 0
    stack = [[]]
    for m in TOK.finditer(text):
        t = m.group(1)
        if t == '(':
            stack.append([])
        elif t == ')':
            l = stack.pop()
            stack[-1].append(l)
        elif t.startswith('"'):
            stack[-1].append(Str(t[1:-1].replace('\\"', '"').replace('\\\\', '\\')))
        else:
            stack[-1].append(t)
    return stack[0][0]

def dump(node, indent=0):
    if isinstance(node, Str):
        return '"' + node.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(node, str):
        return node
    return '(' + ' '.join(dump(n) for n in node) + ')'

def find(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]

def load_symbol(libfile, name):
    """Return the symbol node (flattened if it extends another)."""
    tree = parse(open(libfile).read())
    syms = {c[1]: c for c in tree if isinstance(c, list) and c and c[0] == 'symbol'}
    s = syms[name]
    ext = find(s, 'extends')
    if ext:
        base = load_symbol(libfile, ext[0][1])
        # merge: base graphics/pins with derived properties
        derived_props = {p[1]: p for p in find(s, 'property')}
        out = [base[0], Str(name)]
        for c in base[2:]:
            if isinstance(c, list) and c and c[0] == 'property' and c[1] in derived_props:
                out.append(derived_props[c[1]])
            elif isinstance(c, list) and c and c[0] == 'symbol':
                n = c[1].replace(base[1], name, 1)
                out.append([c[0], Str(n)] + c[2:])
            else:
                out.append(c)
        return out
    return s
