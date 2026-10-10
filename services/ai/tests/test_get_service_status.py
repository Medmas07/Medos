from application.get_service_status import get_service_status
from domain.service_status import ADVISORY_NOTICE


def test_reports_no_capabilities_yet():
    assert get_service_status().capabilities == ()


def test_states_the_advisory_boundary():
    assert get_service_status().notice == ADVISORY_NOTICE
