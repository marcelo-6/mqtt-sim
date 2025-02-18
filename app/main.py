import argparse
from pathlib import Path
from simulator import Simulator


def default_settings():
    """Returns the default settings file path."""
    base_folder = Path(__file__).resolve().parent.parent
    settings_file = base_folder / "config/settings.json"
    return settings_file


def is_valid_file(parser, arg):
    """Validates if the provided file path exists."""
    settings_file = Path(arg)
    if not settings_file.is_file():
        return parser.error(f"argument -f/--file: can't open '{arg}'")
    return settings_file


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Start MQTT Simulator")
    parser.add_argument(
        "-f",
        "--file",
        dest="settings_file",
        type=lambda x: is_valid_file(parser, x),
        help="Path to settings JSON file",
        default=default_settings(),
    )
    args = parser.parse_args()

    # Initialize and run the simulator
    simulator = Simulator(args.settings_file)
    try:
        simulator.run()
    except KeyboardInterrupt:
        print("\nStopping the simulator...")
        simulator.stop()


if __name__ == "__main__":
    main()
