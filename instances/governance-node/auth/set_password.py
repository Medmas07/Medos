"""Set a person's Governance Node password (HC-211, ADR-0010). From the Node's folder:

    python -m auth.set_password usr-olfa

It asks for the password twice and stores only its scrypt hash in
auth/.credentials.json (gitignored, never commit it), or in GOVERNANCE_CREDENTIALS.
The person must be staff or a clinician of the demo dataset (demo-data/people.json).
Restart the Node with GOVERNANCE_AUTH=required for the change to apply.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

from adapters.outbound.credential_file import write_credential
from adapters.outbound.fixture_reviewer_directory import FixtureReviewerDirectory
from adapters.outbound.scrypt_password_hasher import ScryptPasswordHasher

# The same files main.py reads; not imported from it, which would start a Node.
CREDENTIALS_ENV = "GOVERNANCE_CREDENTIALS"
DEFAULT_CREDENTIALS = Path(__file__).resolve().parent / ".credentials.json"
DEMO_DATA_ENV = "GOVERNANCE_NODE_DEMO_DATA"
DEFAULT_DEMO_DATA = Path(__file__).resolve().parents[3] / "demo-data"
MIN_LENGTH = 12


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("person_ref", help="for example usr-olfa")
    args = parser.parse_args()
    demo_data = Path(os.environ.get(DEMO_DATA_ENV, DEFAULT_DEMO_DATA))
    people = FixtureReviewerDirectory.load(demo_data / "people.json")
    if people.reviewer(args.person_ref) is None:
        sys.exit(f"{args.person_ref} is not staff or a clinician of {demo_data}")
    password = getpass.getpass(f"New password for {args.person_ref}: ")
    if len(password) < MIN_LENGTH:
        sys.exit(f"Use at least {MIN_LENGTH} characters.")
    if getpass.getpass("Repeat it: ") != password:
        sys.exit("The passwords differ; nothing was changed.")
    path = Path(os.environ.get(CREDENTIALS_ENV, DEFAULT_CREDENTIALS))
    write_credential(path, args.person_ref, ScryptPasswordHasher().hash(password))
    print(f"Password hash for {args.person_ref} written to {path}.")


if __name__ == "__main__":
    main()
