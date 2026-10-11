"""Compile AuditAnchor.sol into AuditAnchor.json, the artifact the Besu ledger adapter
deploys and calls (HC-194). Run it only after changing the contract:

    pip install py-solc-x==2.0.5
    python ledger/compile_contract.py

py-solc-x downloads the pinned solc release on first use. The artifact records the
source's SHA-256, which the tests compare with the committed source, so the two cannot
drift silently. The EVM version is Berlin, the fork of the dev chain's genesis.
"""

import hashlib
import json
from pathlib import Path

import solcx

SOLC_VERSION = "0.8.26"
EVM_VERSION = "berlin"
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "AuditAnchor.sol"
ARTIFACT = HERE / "AuditAnchor.json"


def source_sha256(source: str) -> str:
    """With LF line endings, whatever the checkout's."""
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def main() -> None:
    solcx.install_solc(SOLC_VERSION)
    source = SOURCE.read_text(encoding="utf-8")
    output = solcx.compile_standard(
        {
            "language": "Solidity",
            "sources": {SOURCE.name: {"content": source}},
            "settings": {
                "evmVersion": EVM_VERSION,
                "optimizer": {"enabled": True, "runs": 200},
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
            },
        },
        solc_version=SOLC_VERSION,
    )
    contract = output["contracts"][SOURCE.name]["AuditAnchor"]
    artifact = {
        "contractName": "AuditAnchor",
        "source": SOURCE.name,
        "sourceSha256": source_sha256(source),
        "compiler": f"solc {SOLC_VERSION}",
        "evmVersion": EVM_VERSION,
        "optimizerRuns": 200,
        "abi": contract["abi"],
        "bytecode": "0x" + contract["evm"]["bytecode"]["object"],
    }
    ARTIFACT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {ARTIFACT.name}")


if __name__ == "__main__":
    main()
