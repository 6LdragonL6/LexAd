import pytest

from app.core.rate_limit import reset_rate_limits


@pytest.fixture(autouse=True)
def _isolate_in_memory_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()
