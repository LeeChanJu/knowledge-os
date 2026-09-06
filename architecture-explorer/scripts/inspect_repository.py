"""Static evidence only. Never import knowledge_os, load .env, or open a database."""

import ast
import hashlib
import json
import sys
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()


class WithoutDocstrings(ast.NodeTransformer):
    def generic_visit(self, node):
        super().generic_visit(node)
        if (
            isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
        ):
            value = node.body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                node.body = node.body[1:]
        return node


def inspect_source(content):
    tree = ast.parse(content)
    symbols = []

    def visit(body, prefix=""):
        for item in body:
            if not isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = prefix + item.name
            decorators = [ast.unparse(d) for d in item.decorator_list]
            if isinstance(item, ast.ClassDef):
                fields = [ast.unparse(f) for f in item.body if isinstance(f, ast.AnnAssign)]
                signature = f"class {name}({', '.join(ast.unparse(b) for b in item.bases)})"
                kind = "class"
            else:
                fields = []
                signature = ("async " if isinstance(item, ast.AsyncFunctionDef) else "")
                signature += f"{name}({ast.unparse(item.args)})"
                if item.returns:
                    signature += f" -> {ast.unparse(item.returns)}"
                kind = "test" if item.name.startswith("test_") else "function"
            record = {
                "symbol": name,
                "kind": kind,
                "signature": signature,
                "decorators": decorators,
                "fields": fields,
            }
            record["fingerprint"] = fingerprint(json.dumps(record, sort_keys=True))
            symbols.append(record)
            if isinstance(item, ast.ClassDef):
                visit(item.body, name + ".")

    visit(tree.body)
    semantic = ast.dump(WithoutDocstrings().visit(tree), include_attributes=False)
    return {"symbols": symbols, "semanticFingerprint": fingerprint(semantic)}


def main():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Explorer evidence requires Python 3.12; set PYTHON to that executable.")
    root = Path(sys.argv[1]).resolve()
    paths = json.load(sys.stdin)
    if len(sys.argv) > 2 and sys.argv[2] == "--contents":
        print(json.dumps({key: inspect_source(value) for key, value in paths.items()}, sort_keys=True))
        return
    output = {}
    for relative in paths:
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Reference escapes repository: {relative}")
        output[relative] = inspect_source(path.read_text(encoding="utf-8"))
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
