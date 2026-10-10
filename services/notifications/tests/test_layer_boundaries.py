"""Enforce Clean Architecture inward dependency boundaries."""

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
INNER_LAYERS = {
    "domain": {"domain"},
    "application": {"domain", "application"},
}


def _imported_roots(path: Path) -> set[str]:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_inner_layers_import_only_inward_or_stdlib():
    for layer, allowed in INNER_LAYERS.items():
        layer_dir = ROOT / layer
        if not layer_dir.exists():
            continue
        for path in layer_dir.rglob("*.py"):
            forbidden = {
                root
                for root in _imported_roots(path)
                if root not in allowed and root not in sys.stdlib_module_names
            }
            assert not forbidden, f"{path.relative_to(ROOT)} imports {forbidden}"
