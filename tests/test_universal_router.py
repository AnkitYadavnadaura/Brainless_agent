import asyncio

from app.autonomy.capability_lifecycle import CapabilityRecord, CapabilityStatus
from app.autonomy.universal_router import UniversalTaskRouter


class Broker:
    class Assessment:
        status = type("Status", (), {"value": "discovery_required"})()

    def assess(self, _goal):
        return self.Assessment()


class Service:
    def __init__(self, status):
        self.status = status
        self.calls = 0

    async def ensure(self, _goal):
        self.calls += 1
        return type("Record", (), {"status": self.status})()


def test_router_acquires_missing_capability_then_retries_execution():
    service = Service(CapabilityStatus.ACTIVE)
    executed = []
    router = UniversalTaskRouter(Broker(), service, lambda goal: _record(executed, goal))
    route, result = asyncio.run(router.run("edit video"))
    assert route.acquired and route.attempts == 1
    assert result == "completed"
    assert executed == ["edit video"]


def test_router_fails_closed_when_acquisition_is_rejected():
    service = Service(CapabilityStatus.REJECTED)
    router = UniversalTaskRouter(Broker(), service, lambda _: _record([], "never"))
    try:
        asyncio.run(router.run("edit video"))
    except RuntimeError as error:
        assert "acquisition failed" in str(error)
    else:
        raise AssertionError("Rejected capability was executed")


async def _record(values, value):
    values.append(value)
    return "completed"
