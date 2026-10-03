from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import paho.mqtt.client as mqtt

from simulator.generator import generate_telemetry
from src.mqtt_ingress import DEFAULT_PORT, encode_telemetry


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish fake telemetry to MQTT.")
    parser.add_argument("--num-devices", type=int, default=10)
    parser.add_argument("--events-per-device", type=int, default=100)
    parser.add_argument("--duplicate-pct", type=float, default=0.10)
    parser.add_argument("--out-of-order-pct", type=float, default=0.05)
    parser.add_argument("--late-pct", type=float, default=0.02)
    parser.add_argument("--window-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--boot-id", default="")
    parser.add_argument("--prefix", default="telemetry")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    try:
        from paho.mqtt.client import CallbackAPIVersion

        client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1)
    except ImportError:
        client = mqtt.Client()
    client.connect(args.host, args.port)
    client.loop_start()

    sent = 0
    for event in generate_telemetry(
        num_devices=args.num_devices,
        events_per_device=args.events_per_device,
        duplicate_pct=args.duplicate_pct,
        out_of_order_pct=args.out_of_order_pct,
        late_pct=args.late_pct,
        window_size=args.window_size,
        seed=args.seed,
        boot_id=args.boot_id,
    ):
        topic = f"{args.prefix}/{event.device_id}"
        client.publish(topic, encode_telemetry(event))
        sent += 1

    # give the network loop a moment to flush
    time.sleep(1.0)
    client.loop_stop()
    client.disconnect()
    print(f"published {sent} messages to {args.host}:{args.port}")


if __name__ == "__main__":
    main()
