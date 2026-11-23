"""
@example DomusAPI_3_events.py

Subscribe to a Domus event and publish an application event.
"""

from threading import Event

import DomusAPI
from DomusEvents import EventType


def main() -> None:
    received = Event()

    def on_state_change(event) -> None:
        print(f"{event.type}: {event.payload}")
        received.set()

    subscription = DomusAPI.subscribe(EventType.STATE_CHANGED, on_state_change)
    try:
        DomusAPI.publish(
            EventType.STATE_CHANGED,
            payload={"component": "example", "state": "ready"},
        )
        # Event callbacks run on the bus worker thread.
        received.wait(timeout=2)
    finally:
        subscription.unsubscribe()
        DomusAPI.shutdown()


if __name__ == "__main__":
    main()