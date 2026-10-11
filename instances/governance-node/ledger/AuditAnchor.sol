// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.26;

/// HC-194 (ADR-0007): the Governance Node's decision proofs on a permissioned
/// Hyperledger Besu (QBFT) ledger, behind its AuditLedgerPort.
///
/// Holds, for each governance audit event anchored, the canonical minimized proof
/// payload (domain/ledger.py `canonical_payload`: six fields, references, an outcome,
/// a time, organizations, and a version; never clinical content) and its SHA-256,
/// computed here. Append-only: an event is anchored once, and nothing is changed or
/// removed. Only the account that deployed it, the Governance Node's, may anchor.
contract AuditAnchor {
    struct Anchor {
        string eventRef;
        string payload;
        bytes32 payloadHash;
        uint64 anchoredAt;
    }

    address public immutable authority;
    Anchor[] private anchors;
    // The index of each anchored event plus one; 0 when not anchored.
    mapping(string => uint256) private positions;

    event Anchored(uint256 indexed index, string eventRef, bytes32 payloadHash);

    error NotAuthority();
    error EmptyAnchor();
    error AlreadyAnchored(string eventRef);

    constructor() {
        authority = msg.sender;
    }

    function anchor(string calldata eventRef, string calldata payload)
        external
        returns (uint256 index)
    {
        if (msg.sender != authority) revert NotAuthority();
        if (bytes(eventRef).length == 0 || bytes(payload).length == 0) {
            revert EmptyAnchor();
        }
        if (positions[eventRef] != 0) revert AlreadyAnchored(eventRef);
        bytes32 payloadHash = sha256(bytes(payload));
        anchors.push(Anchor(eventRef, payload, payloadHash, uint64(block.timestamp)));
        index = anchors.length - 1;
        positions[eventRef] = anchors.length;
        emit Anchored(index, eventRef, payloadHash);
    }

    function count() external view returns (uint256) {
        return anchors.length;
    }

    function anchorAt(uint256 index) external view returns (Anchor memory) {
        return anchors[index];
    }

    /// Whether the event is anchored, and at which index.
    function find(string calldata eventRef)
        external
        view
        returns (bool found, uint256 index)
    {
        uint256 position = positions[eventRef];
        if (position == 0) return (false, 0);
        return (true, position - 1);
    }
}
