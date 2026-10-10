"""Isolated stdlib-only worker for the single installed research aggregate."""

import json
import sys

MAX_INPUT_BYTES = 262_144


def _apply_resource_limits() -> str:
    try:
        import resource
    except ImportError:
        return "parent_enforced"
    resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024,) * 2)
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    return "posix_rlimit"


def _deny_external_access(event: str, _arguments: tuple) -> None:
    if (
        event == "open"
        or event == "import"
        or event.startswith(("socket.", "subprocess.", "os.system", "os.spawn"))
    ):
        raise PermissionError(f"sandbox denied {event}")


def main() -> int:
    resource_mode = _apply_resource_limits()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("sandbox input limit exceeded")
    payload = json.loads(raw)
    sys.addaudithook(_deny_external_access)

    subjects = payload["subjects"]
    minimum = payload["minimum_cell_size"]
    if not subjects:
        outcome, columns, rows, reason = "empty", [], [], None
    elif len(subjects) < minimum:
        outcome, columns, rows, reason = (
            "suppressed",
            [],
            [],
            "minimum_cell_size",
        )
    else:
        values = [value for subject in subjects for value in subject["hba1c_values"]]
        if not values:
            outcome, columns, rows, reason = "empty", [], [], None
        else:
            percentage = round(
                100 * sum(value > 7 for value in values) / len(values), 1
            )
            outcome = "released"
            columns = ["participant_count", "hba1c_above_7_pct"]
            rows = [[len(subjects), percentage]]
            reason = None
    print(
        json.dumps(
            {
                "outcome": outcome,
                "columns": columns,
                "rows": rows,
                "reason_code": reason,
                "resource_mode": resource_mode,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
