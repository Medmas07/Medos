from application.get_node_status import get_node_status
from domain.node_status import SKELETON_NOTICE


def test_reports_no_capabilities_yet():
    assert get_node_status().capabilities == ()


def test_states_the_skeleton_boundary():
    assert get_node_status().notice == SKELETON_NOTICE
