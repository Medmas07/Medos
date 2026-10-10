from application.get_node_status import get_node_status
from domain.node_identity import NodeIdentity
from domain.node_status import SKELETON_NOTICE

IDENTITY = NodeIdentity(node_ref="node-test", organization_ref="org-test")


def test_reports_the_configured_hospital_identity():
    status = get_node_status(IDENTITY)

    assert (status.node_ref, status.organization_ref) == ("node-test", "org-test")


def test_reports_no_capabilities_yet():
    assert get_node_status(IDENTITY).capabilities == ()


def test_states_the_skeleton_boundary():
    assert get_node_status(IDENTITY).notice == SKELETON_NOTICE
