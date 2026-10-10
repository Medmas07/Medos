"""RFC 9457 problem details, as the Governance Node's contracts define them."""

import re

from fastapi.responses import JSONResponse
from pydantic import ValidationError

# OpaqueRef in every contract.
OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def problem(
    status: int, title: str, code: str, detail: str, **extra: object
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
            **extra,
        },
    )


def first_error(error: ValidationError) -> str:
    """'field: message' for the first invalid field; 'body' for malformed JSON."""
    first = error.errors()[0]
    return f"{'.'.join(map(str, first['loc'])) or 'body'}: {first['msg']}"
