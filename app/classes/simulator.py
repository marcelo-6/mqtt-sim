import json
from pathlib import Path
from typing import List
from .data_classes import BrokerSettings, ClientSettings
from .topic import Topic, TopicConfig
from pydantic import ValidationError


class Simulator:
    def __init__(self, settings_file: Path):
        self.default_client_settings = ClientSettings(
            clean=True, retain=False, qos=2, time_interval=10
        )
        self.topics: List[Topic] = []
        self.load_topics(settings_file)

    def read_client_settings(
        self, settings_dict: dict, default: ClientSettings
    ) -> ClientSettings:
        """Reads client settings from the given dictionary."""
        return ClientSettings(
            clean=settings_dict.get("clean_session", default.clean),
            retain=settings_dict.get("retain", default.retain),
            qos=settings_dict.get("qos", default.qos),
            time_interval=settings_dict.get("time_interval", default.time_interval),
        )

    def load_topics(self, settings_file: Path) -> None:
        """Loads and validates topics from the provided settings file."""
        try:
            with open(settings_file, "r") as f:
                config = json.load(f)

            broker_settings = BrokerSettings(
                url=config.get("broker_url", "localhost"),
                port=config.get("broker_port", 1883),
                protocol_version=config.get("protocol_version", 4),
            )

            broker_client_settings = self.read_client_settings(
                config, self.default_client_settings
            )

            for topic_config_data in config.get("topics", []):
                try:
                    # Validate and create TopicConfig using Pydantic
                    topic_config = TopicConfig(**topic_config_data)

                    # Initialize each topic based on its configuration
                    topic = Topic(
                        broker_settings=broker_settings,
                        topic_url=topic_config.prefix,
                        topic_config=topic_config,
                        client_settings=broker_client_settings,
                    )
                    self.topics.append(topic)
                except ValidationError as e:
                    print(f"Error in topic configuration: {e}")
                except Exception as e:
                    print(f"Failed to create topic: {e}")
            print("Topics loaded")

        except FileNotFoundError:
            print(f"Settings file not found: {settings_file}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from settings file: {settings_file}")

    def run(self) -> None:
        """Starts the simulation by running each topic as a separate thread."""
        for topic in self.topics:
            print(f"Starting: {topic.topic_url} ...")
            topic.start()

        for topic in self.topics:
            # Workaround for Python 3.12 (ensure the thread joins correctly)
            topic.join()

    def stop(self) -> None:
        """Stops the simulation by stopping each topic."""
        for topic in self.topics:
            print(f"Stopping: {topic.topic_url} ...")
            topic.disconnect()
