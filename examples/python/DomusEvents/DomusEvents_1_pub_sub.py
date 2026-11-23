"""@examples
Create the event bus, publish an event, and release the subscription."""

from threading import Event

import DomusEvents


def main() -> None:
    received = Event()

    def on_event(event) -> None:
        print(f"received {event.type}: {event.payload}")
        received.set()

    bus = DomusEvents.initialize_bus()
    subscription = bus.subscribe(DomusEvents.EventType.CUSTOM, on_event)
    try:
        DomusEvents.publish_event(
            DomusEvents.EventType.CUSTOM,
            source="example",
            payload={"message": "hello"},
        )
        received.wait(timeout=2)
    finally:
        subscription.unsubscribe()
        DomusEvents.shutdown_bus()


if __name__ == "__main__":
    main()