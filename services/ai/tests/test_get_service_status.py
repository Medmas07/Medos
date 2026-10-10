from application.get_service_status import get_service_status
from domain.service_status import ADVISORY_NOTICE


def test_reports_only_mocked_capabilities():
    capabilities = get_service_status().capabilities
    assert capabilities == ("clinical-extraction:mocked",)
    assert all(c.endswith(":mocked") for c in capabilities)


def test_states_the_advisory_boundary():
    assert get_service_status().notice == ADVISORY_NOTICE
