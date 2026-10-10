import pytest

from application.get_node_status import get_node_status
from domain.node_identity import InvalidNodeIdentity, NodeIdentity
from domain.node_status import SKELETON_NOTICE


def test_status_names_the_node_and_its_capabilities():
    status = get_node_status(NodeIdentity("node-governance", "org-governance"))

    assert status.node == "governance-node"
    assert status.node_ref == "node-governance"
    assert status.organization_ref == "org-governance"
    assert status.capabilities == ("hospital_approval", "synchronization")
    assert status.notice == SKELETON_NOTICE


def test_notice_states_what_is_not_implemented():
    for phrase in (
        "PLANNED",
        "not authenticated",
        "lost on restart",
        "not a production",
    ):
        assert phrase in SKELETON_NOTICE


@pytest.mark.parametrize("bad", ["", " org", "org governance", "-org", "x" * 129])
def test_identity_refs_must_be_opaque(bad):
    with pytest.raises(InvalidNodeIdentity):
        NodeIdentity(node_ref="node-governance", organization_ref=bad)
    with pytest.raises(InvalidNodeIdentity):
        NodeIdentity(node_ref=bad, organization_ref="org-governance")
