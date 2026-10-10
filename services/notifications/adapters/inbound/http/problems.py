"""RFC 9457 Problem Details responses."""

from fastapi.responses import JSONResponse


def problem_response(
    status: int, title: str, detail: str, type_uri: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": type_uri,
            "title": title,
            "status": status,
            "detail": detail,
        },
    )
