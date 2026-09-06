"""Tests for documentation AST inspection only; no production imports or services."""

import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "inspect_repository.py"
SPEC = importlib.util.spec_from_file_location("explorer_inspector", PATH)
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)


def test_comments_docstrings_and_whitespace_do_not_change_evidence():
    first = '"""Module docs."""\ndef fn(x: int) -> int:\n    """A docstring."""\n    return x\n'
    second = "# Comment\n\ndef fn(x:int)->int:\n    return x\n"
    assert inspector.inspect_source(first) == inspector.inspect_source(second)


def test_body_change_is_distinct_from_interface_change():
    first = inspector.inspect_source("def fn(x: int):\n    return x\n")
    second = inspector.inspect_source("def fn(x: int):\n    return x + 1\n")
    assert first["symbols"] == second["symbols"]
    assert first["semanticFingerprint"] != second["semanticFingerprint"]


def test_qualified_symbols_fields_decorators_and_async_are_preserved():
    source = """
class Model:
    size: int = 4
    def validate(self):
        pass

@app.get('/v1/example')
async def read_example(limit: int = 5):
    pass

def test_example():
    assert True
"""
    symbols = {s["symbol"]: s for s in inspector.inspect_source(source)["symbols"]}
    assert symbols["Model"]["fields"] == ["size: int = 4"]
    assert symbols["Model.validate"]["signature"] == "Model.validate(self)"
    assert symbols["read_example"]["signature"].startswith("async ")
    assert symbols["read_example"]["decorators"] == ["app.get('/v1/example')"]
    assert symbols["test_example"]["kind"] == "test"
