"""Create the Governance Node's federation signing key (HC-214, ADR-0015). From the
Node's folder:

    python -m auth.create_signing_key

It writes a new Ed25519 private key to auth/.signing-key.pem (gitignored, never commit
it), or to GOVERNANCE_SIGNING_KEY, and its public key next to it, with `.pub.pem` in
place of `.pem`. Give the public key to each Hospital Node that should trust this Node
(`governance_public_key` in its configuration). It refuses to replace an existing key:
delete it first, and redistribute the new public key, to rotate it. Restart the Node
with GOVERNANCE_FEDERATION_SIGNING=ed25519 for signing to apply.
"""

import argparse
import os
import sys
from pathlib import Path

from adapters.outbound.ed25519_authorization_signer import Ed25519AuthorizationSigner

# The same file main.py reads; not imported from it, which would start a Node.
SIGNING_KEY_ENV = "GOVERNANCE_SIGNING_KEY"
DEFAULT_SIGNING_KEY = Path(__file__).resolve().parent / ".signing-key.pem"


def public_key_path(private_key: Path) -> Path:
    return private_key.with_name(private_key.name.removesuffix(".pem") + ".pub.pem")


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    path = Path(os.environ.get(SIGNING_KEY_ENV, DEFAULT_SIGNING_KEY))
    if path.exists():
        sys.exit(f"{path} already exists; nothing was changed.")
    signer = Ed25519AuthorizationSigner.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Readable by its owner only, where the platform honours the mode.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as file:
        file.write(signer.private_key_pem())
    public = public_key_path(path)
    public.write_bytes(signer.public_key_pem())
    print(f"Private key written to {path}.")
    print(f"Public key (key id {signer.key_id}) written to {public}.")


if __name__ == "__main__":
    main()
