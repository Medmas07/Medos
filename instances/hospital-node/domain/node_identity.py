import re
from dataclasses import dataclass

# Same rule as OpaqueRef in contracts/federation/hospital-node-federation.v1.yaml.
_OPAQUE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


class InvalidNodeIdentity(ValueError):
    pass


@dataclass(frozen=True)
class NodeIdentity:
    """Which hospital this Node instance runs for. One process per hospital."""

    node_ref: str
    organization_ref: str

    def __post_init__(self) -> None:
        for field in ("node_ref", "organization_ref"):
            if not _OPAQUE_REF.fullmatch(getattr(self, field)):
                raise InvalidNodeIdentity(f"{field} must be an opaque reference")
