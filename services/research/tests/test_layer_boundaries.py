from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_domain_and_application_do_not_import_framework_or_http_clients():
    forbidden = ("fastapi", "pydantic", "httpx")
    for layer in ("domain", "application"):
        for path in (ROOT / layer).glob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert not any(name in source for name in forbidden), path
