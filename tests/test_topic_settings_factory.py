from __future__ import annotations

from settings_classes.topic_settings_factory import TopicSettingsFactory


def test_topic_settings_factory_builds_list_topics() -> None:
    topic = TopicSettingsFactory.create(
        {
            "TYPE": "list",
            "PREFIX": "device",
            "LIST": ["a", "b"],
            "DATA": [{"NAME": "x", "TYPE": "bool"}],
        }
    )

    assert topic.topic_urls() == ["device/a", "device/b"]
    assert topic.payload_root == {}
