from application.get_service_status import get_service_status
from domain.service_status import ADVISORY_NOTICE


def test_reports_the_configured_capabilities():
    status = get_service_status(("clinical-extraction:model",))
    assert status.capabilities == ("clinical-extraction:model",)


def test_states_the_advisory_boundary():
    assert get_service_status(()).notice == ADVISORY_NOTICE
