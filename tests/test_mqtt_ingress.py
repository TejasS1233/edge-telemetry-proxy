from __future__ import annotations

import json

import pytest

from src.dedup import DedupStatus
from src.mqtt_ingress import MqttIngress, encode_telemetry, parse_telemetry
from src.pipeline import Decision, EdgePipeline
from src.telemetry import Telemetry


def test_parse_full_payload():
    payload = json.dumps(
        {"device_id": "dev-1", "sequence": 7, "timestamp": 123.0, "metric": "humidity", "value": 55.5}
    )
    t = parse_telemetry("telemetry/dev-9", payload)
    assert t.device_id == "dev-1"
    assert t.sequence == 7
    assert t.timestamp == 123.0
    assert t.metric == "humidity"
    assert t.value == 55.5


def test_parse_device_falls_back_to_topic():
    payload = json.dumps({"sequence": 3, "value": 21.0})
    t = parse_telemetry("telemetry/device-00001", payload)
    assert t.device_id == "device-00001"
    assert t.sequence == 3
    # sane defaults fill the rest
    assert t.metric == "temperature"


def test_parse_bytes_payload():
    t = parse_telemetry("telemetry/a", b'{"sequence": 1, "value": 2.5}')
    assert t.device_id == "a"
    assert t.sequence == 1


def test_parse_bad_json_raises():
    with pytest.raises(ValueError):
        parse_telemetry("telemetry/a", "not json{")


def test_parse_non_object_raises():
    with pytest.raises(ValueError):
        parse_telemetry("telemetry/a", "[1, 2]")


def test_parse_missing_sequence_raises():
    with pytest.raises(ValueError):
        parse_telemetry("telemetry/a", '{"value": 1.0}')


def test_parse_missing_value_raises():
    with pytest.raises(ValueError):
        parse_telemetry("telemetry/a", '{"sequence": 1}')


def test_encode_roundtrip():
    t = Telemetry(device_id="d1", sequence=5, timestamp=1.0, metric="temperature", value=20.0)
    back = parse_telemetry("telemetry/d1", encode_telemetry(t))
    assert back == t


def test_handle_message_forwards_new_and_drops_dupe():
    ingress = MqttIngress(pipeline=EdgePipeline(window_size=5))
    payload = json.dumps({"sequence": 100, "value": 20.0})
    first = ingress.handle_message("telemetry/dev-1", payload)
    assert first.decision == Decision.FORWARD
    assert first.dedup.status == DedupStatus.NEW
    second = ingress.handle_message("telemetry/dev-1", payload)
    assert second.decision == Decision.DROP
    assert second.dedup.status == DedupStatus.DUPLICATE
    assert ingress.forwarded == 1
    assert ingress.dropped == 1


def test_handle_message_bad_payload_returns_none():
    ingress = MqttIngress(pipeline=EdgePipeline(window_size=5))
    assert ingress.handle_message("telemetry/dev-1", "garbage{") is None
    assert ingress.dropped == 1
