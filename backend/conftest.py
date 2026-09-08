"""
Test-wide fixtures.

The suite runs against whichever settings module is active — desktop locally,
dev in CI — so throttling is disabled here rather than in one settings file.
A test class that signs in for every test would otherwise trip the login
throttle and fail for a reason that has nothing to do with what it tests.
Throttling stays on in every real deployment.
"""

import pytest
from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


@pytest.fixture(autouse=True)
def _no_throttling(settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"anon": None, "user": None, "login": None},
    }
    # DRF reads the rate once, at construction, from the class attribute.
    SimpleRateThrottle.THROTTLE_RATES = {"anon": None, "user": None, "login": None}
    ScopedRateThrottle.THROTTLE_RATES = {"anon": None, "user": None, "login": None}
    cache.clear()
    yield
    cache.clear()
