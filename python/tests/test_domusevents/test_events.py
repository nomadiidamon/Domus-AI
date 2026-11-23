"""Tests for DomusEvents: the Domus event vocabulary and process-wide bus."""

import time

import pytest

import DomusEvents
from DomusEvents import EventType

pytestmark = pytest.mark.domusevents


@pytest.fixture(autouse=True)
def _reset_bus():
    DomusEvents.shutdown_bus(drain=False)
    yield
    DomusEvents.shutdown_bus(drain=False)


def _wait_for(items, count=1, timeout=2.0):
    deadline = time.time() + timeout
    while len(items) < count and time.time() < deadline:
        time.sleep(0.01)


class TestLifecycle:
    def test_get_bus_none_before_init(self):
        assert DomusEvents.get_bus() is None

    def test_initialize_bus_is_idempotent(self):
        first = DomusEvents.initialize_bus()
        assert first.is_running
        assert DomusEvents.initialize_bus() is first
        assert DomusEvents.get_bus() is first

    def test_initialize_after_stop_restarts_same_bus(self):
        bus = DomusEvents.initialize_bus()
        bus.stop(drain=False)
        assert DomusEvents.initialize_bus() is bus
        assert bus.is_running

    def test_shutdown_clears_bus_and_is_safe_twice(self):
        bus = DomusEvents.initialize_bus()
        DomusEvents.shutdown_bus()
        assert DomusEvents.get_bus() is None
        assert bus.is_closed
        DomusEvents.shutdown_bus()

    def test_initialize_after_shutdown_creates_new_bus(self):
        first = DomusEvents.initialize_bus()
        DomusEvents.shutdown_bus()
        assert DomusEvents.initialize_bus() is not first


class TestPublish:
    def test_publish_without_bus_is_noop(self):
        DomusEvents.publish_event(EventType.CUSTOM, source="test")

    def test_publish_delivers_string_typed_event(self):
        bus = DomusEvents.initialize_bus()
        received = []
        bus.subscribe(EventType.MODEL_LOADED, received.append)
        DomusEvents.publish_event(EventType.MODEL_LOADED, source="s", payload={"k": 1})
        _wait_for(received)
        assert len(received) == 1
        event = received[0]
        assert type(event.type) is str
        assert event.type == "model_loaded"
        assert event.source == "s"
        assert event.payload == {"k": 1}

    def test_subscribe_by_plain_string_matches(self):
        bus = DomusEvents.initialize_bus()
        received = []
        bus.subscribe("custom", received.append)
        DomusEvents.publish_event(EventType.CUSTOM)
        _wait_for(received)
        assert len(received) == 1

    def test_unsubscribed_callback_not_called(self):
        bus = DomusEvents.initialize_bus()
        received = []
        sub = bus.subscribe(EventType.CUSTOM, received.append)
        sub.unsubscribe()
        DomusEvents.publish_event(EventType.CUSTOM)
        time.sleep(0.1)
        assert received == []


def test_event_type_values_are_unique_strings():
    values = [e.value for e in EventType]
    assert len(values) == len(set(values))
    assert all(isinstance(v, str) for v in values)
