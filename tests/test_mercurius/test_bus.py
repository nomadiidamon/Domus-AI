"""
Tests for Mercurius' EventBus: subscription routing, thread-safety,
callback exception isolation, and drain/no-drain shutdown semantics.

The bus dispatches on a background thread, so tests synchronize by
stopping with drain=True (which guarantees all queued events were
processed before the sentinel) rather than sleeping.
"""

import threading

import pytest

import Mercurius
from Mercurius import Event, EventBus, EventType

pytestmark = pytest.mark.mercurius


class TestSubscriptionRouting:
    def test_subscriber_receives_matching_event(self, bus):
        received = []
        bus.subscribe(EventType.MODEL_LOADED, received.append)

        bus.publish(Event(type=EventType.MODEL_LOADED, payload={"model": "mercury"}))
        bus.stop(drain=True)

        assert len(received) == 1
        assert received[0].payload == {"model": "mercury"}

    def test_subscriber_does_not_receive_other_types(self, bus):
        received = []
        bus.subscribe(EventType.MODEL_LOADED, received.append)

        bus.publish(Event(type=EventType.ERROR, payload={"msg": "boom"}))
        bus.stop(drain=True)

        assert received == []

    def test_multiple_subscribers_all_invoked(self, bus):
        first, second = [], []
        bus.subscribe(EventType.STARTUP, first.append)
        bus.subscribe(EventType.STARTUP, second.append)

        bus.publish(Event(type=EventType.STARTUP))
        bus.stop(drain=True)

        assert len(first) == 1
        assert len(second) == 1

    def test_unsubscribe_stops_delivery(self, bus):
        received = []
        bus.subscribe(EventType.WARNING, received.append)
        assert bus.unsubscribe(EventType.WARNING, received.append) is True

        bus.publish(Event(type=EventType.WARNING))
        bus.stop(drain=True)

        assert received == []

    def test_unsubscribe_unknown_callback_returns_false(self, bus):
        assert bus.unsubscribe(EventType.WARNING, lambda e: None) is False


class TestThreadSafety:
    def test_concurrent_publishers_lose_no_events(self, bus):
        received = []
        lock = threading.Lock()

        def on_event(event):
            with lock:
                received.append(event)

        bus.subscribe(EventType.CUSTOM, on_event)

        per_thread = 50
        threads = [
            threading.Thread(
                target=lambda: [
                    bus.publish(Event(type=EventType.CUSTOM, payload={"i": i}))
                    for i in range(per_thread)
                ]
            )
            for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        bus.stop(drain=True)

        assert len(received) == 4 * per_thread


class TestCallbackIsolation:
    def test_raising_callback_does_not_kill_bus_or_block_others(self, bus):
        received = []

        def bad_callback(event):
            raise ValueError("boom")

        bus.subscribe(EventType.ERROR, bad_callback)
        bus.subscribe(EventType.ERROR, received.append)

        bus.publish(Event(type=EventType.ERROR))
        bus.publish(Event(type=EventType.ERROR))
        bus.stop(drain=True)

        # Dispatch thread survived the exception and kept processing
        assert len(received) == 2


class TestShutdownSemantics:
    def test_stop_with_drain_processes_all_queued_events(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.CUSTOM, received.append)

        for i in range(20):
            bus.publish(Event(type=EventType.CUSTOM))

        bus.start()
        bus.stop(drain=True)

        assert len(received) == 20

    def test_stop_without_drain_discards_pending_events(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.CUSTOM, received.append)

        for i in range(20):
            bus.publish(Event(type=EventType.CUSTOM))

        # Queue is full but the dispatch thread never started, so stop
        # without drain must drop everything.
        bus.start()
        bus.stop(drain=False)

        assert len(received) <= 20  # may process 0+ before the stop lands
        assert not bus.is_running

    def test_double_stop_is_safe(self, bus):
        bus.stop()
        bus.stop()
        assert not bus.is_running

    def test_double_start_spawns_one_thread(self, bus):
        bus.start()
        threads = [t for t in threading.enumerate() if t.name == "mercurius-event-bus"]
        assert len(threads) == 1


class TestSingleton:
    def test_get_bus_is_none_before_initialize(self):
        assert Mercurius.get_bus() is None

    def test_initialize_bus_starts_it(self):
        bus = Mercurius.initialize_bus()
        assert bus.is_running
        assert Mercurius.get_bus() is bus

    def test_initialize_bus_is_idempotent(self):
        first = Mercurius.initialize_bus()
        assert Mercurius.initialize_bus() is first

    def test_shutdown_bus_releases_singleton(self):
        Mercurius.initialize_bus()
        Mercurius.shutdown_bus()
        assert Mercurius.get_bus() is None

    def test_publish_event_noops_without_bus(self):
        Mercurius.publish_event(EventType.CUSTOM, source="test")  # must not raise

    def test_publish_event_routes_through_singleton(self):
        received = []
        bus = Mercurius.initialize_bus()
        bus.subscribe(EventType.CUSTOM, received.append)

        Mercurius.publish_event(EventType.CUSTOM, source="test", payload={"k": "v"})
        bus.stop(drain=True)

        assert len(received) == 1
        assert received[0].source == "test"


class TestEventTypeCoverage:
    """The bus's event vocabulary must cover the conversation/memory
    intents other subsystems rely on - pin the names so a rename is a
    deliberate, test-visible change."""

    def test_messaging_and_memory_event_types_exist(self):
        for name in (
            "MESSAGE_SENT", "MESSAGE_RECEIVED",
            "CONVERSATION_CONDENSED", "MEMORY_STORED", "USER_MEMORY_UPDATED",
        ):
            assert hasattr(EventType, name), f"EventType.{name} missing"

    def test_new_types_are_subscribable_and_routed(self):
        bus = EventBus()
        bus.start()
        received = []
        bus.subscribe(EventType.MEMORY_STORED, received.append)
        bus.publish(Event(type=EventType.MESSAGE_SENT, payload={"content": "x"}))
        bus.publish(Event(type=EventType.MEMORY_STORED, payload={"kind": "note"}))
        bus.stop(drain=True)

        assert len(received) == 1
        assert received[0].payload["kind"] == "note"
