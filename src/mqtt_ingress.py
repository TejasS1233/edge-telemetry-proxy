from __future__ import annotations

import argparse
import json
import time

import paho.mqtt.client as mqtt

from .pipeline import EdgePipeline

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 1883
DEFAULT_TOPIC = "telemetry/#"
DEFAULT_PREFIX = "telemetry"


def parse_telemetry(topic: str, payload: bytes | str):
    from .telemetry import Telemetry

    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"bad JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")

    # device id comes from payload, else from topic tail
    device_id = data.get("device_id") or topic.split("/")[-1]
    if not device_id:
        raise ValueError("missing device_id")

    if "sequence" not in data:
        raise ValueError("missing sequence")
    if "value" not in data:
        raise ValueError("missing value")

    return Telemetry(
        device_id=str(device_id),
        sequence=int(data["sequence"]),
        timestamp=float(data.get("timestamp", time.time())),
        metric=str(data.get("metric", "temperature")),
        value=float(data["value"]),
        boot_id=str(data.get("boot_id", "")),
    )


def encode_telemetry(telemetry) -> str:
    return json.dumps(
        {
            "device_id": telemetry.device_id,
            "sequence": telemetry.sequence,
            "timestamp": telemetry.timestamp,
            "metric": telemetry.metric,
            "value": telemetry.value,
            "boot_id": telemetry.boot_id,
        }
    )


class MqttIngress:
    def __init__(
        self,
        pipeline: EdgePipeline | None = None,
        window_size: int = 32,
        broker_host: str = DEFAULT_HOST,
        broker_port: int = DEFAULT_PORT,
        topic: str = DEFAULT_TOPIC,
    ) -> None:
        self.pipeline = pipeline or EdgePipeline(window_size=window_size)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.forwarded = 0
        self.dropped = 0
        self.client: mqtt.Client | None = None

    # called directly in tests, and from paho callback in prod
    def handle_message(self, topic: str, payload: bytes | str):
        from .pipeline import Decision

        try:
            telemetry = parse_telemetry(topic, payload)
        except ValueError as e:
            # junk in, just log and move on
            print(f"DROP bad message on {topic}: {e}")
            self.dropped += 1
            return None
        result = self.pipeline.process(telemetry)
        if result.decision == Decision.FORWARD:
            self.forwarded += 1
        else:
            self.dropped += 1
        print(f"{result.decision.value} {telemetry.device_id} seq={telemetry.sequence} ({result.dedup.status.value})")
        return result

    def _on_message(self, _client, _userdata, msg):
        self.handle_message(msg.topic, msg.payload)

    def start(self) -> None:
        try:
            from paho.mqtt.client import CallbackAPIVersion

            self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1)
        except ImportError:
            self.client = mqtt.Client()
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, self.broker_port)
        self.client.subscribe(self.topic)
        print(f"listening on {self.broker_host}:{self.broker_port} topic {self.topic}")
        self.client.loop_forever()

    def stop(self) -> None:
        if self.client is not None:
            self.client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge proxy MQTT ingress.")
    parser.add_argument("--broker-host", default=DEFAULT_HOST)
    parser.add_argument("--broker-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--window-size", type=int, default=32)
    args = parser.parse_args()
    ingress = MqttIngress(
        window_size=args.window_size,
        broker_host=args.broker_host,
        broker_port=args.broker_port,
        topic=args.topic,
    )
    try:
        ingress.start()
    except KeyboardInterrupt:
        print(f"\ndone: forwarded={ingress.forwarded} dropped={ingress.dropped}")


if __name__ == "__main__":
    main()
