"""
@example DomusAPI_1_lifecycle.py

Initialize the runtime, inspect hardware, and shut down cleanly.
"""

import DomusAPI
from utils import livy


def main() -> None:
    # Runtime state is stored in the selected host project.
    context = DomusAPI.init(suggested_host=".")
    try:
        hardware = DomusAPI.detect_hardware()
        print(hardware.primary_accelerator)
        print(context.get_system_status())
        print(f"Runtime log: {livy.log_file}")
    finally:
        DomusAPI.shutdown()


if __name__ == "__main__":
    main()