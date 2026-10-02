# edge-telemetry-proxy

A prototype for an edge box that sits between IoT devices and the cloud, drops duplicate telemetry locally, and only forwards fresh stuff upstream.

Im basically trying out ideas for something like the AWS IoT SiteWise Edge MQTT Gateway. That thing collects, buffers and forwards sensor data at the edge and yes ik realistically its all wasm and rust BUT this is just a sort of conceptual understanding.

Things I have read till now and u can too if you are interested:
- https://docs.aws.amazon.com/iot-sitewise/latest/userguide/mqtt-enabled-v3-gateway.html
- https://azure.github.io/iotedge-lorawan-starterkit/dev/quickstart/

personally I didnt really like the path filters part , i think there is tons of scope in it and ill prolly think of a way to implement smth

Also read many articles on from like the first party(mqtt providers and bloomfilter articles etc HIGHLY recommend reading)

## Engineering Journey

This project is being built as an ongoing systems investigation rather than a predefined implementation.

Im documenting the decisions, failed assumptions, experiments and performance tradeoffs as the architecture evolves.

- [Read the Engineering Journey](docs/journey/README.md)
- [Decision records](docs/decisions/ADR-001-exact-dedup.md)
- [Benchmark numbers](docs/experiments/dedup-results.md)

## Architecture

Now with local MQTT ingress:

```
fake devices (mqtt_publisher)
  -> local mosquitto broker (localhost:1883, topic telemetry/#)
  -> edge proxy (mqtt_ingress, subscribes, parses JSON)
  -> EdgePipeline -> dedup check -> FORWARD or DROP
```

The old direct path still works too (simulator generator straight into the pipeline, used by the benchmark).

Files:

* `src/telemetry.py` - the event shape: device_id, sequence, timestamp, metric, value
* `src/dedup.py` - per device sliding window dedup, returns NEW / DUPLICATE / TOO_OLD
* `src/pipeline.py` - NEW means FORWARD, everything else means DROP. Has an `add_stage()` hook so anomaly detection can plug in later
* `src/mqtt_ingress.py` - subscribes to telemetry/#, parses JSON into Telemetry, feeds the pipeline, prints FORWARD or DROP
* `src/config.py` - workload settings plus MqttConfig (host, port, topic)
* `simulator/generator.py` - fake devices with dupes, out of order and late packets
* `simulator/mqtt_publisher.py` - publishes generated telemetry to the broker over MQTT
* `benchmarks/benchmark_dedup.py` - load test + stats (no broker needed)
* `tests/test_dedup.py` - dedup pytest suite
* `tests/test_mqtt_ingress.py` - MQTT parse/convert tests, no broker needed

## how dedup works

Each device has its own counter. `(device_id, sequence)` is the key.

Per device I keep:

* `max_seq` - highest seq seen so far
* `seen` - set of seqs inside `[max_seq - window + 1, max_seq]`

Then:

* in `seen` -> DUPLICATE
* below the window -> TOO_OLD
* else -> NEW (and slide the window if it is a new high)

Just a dict of sets. Simple, exact, O(window) memory per device. Good enough for now. A bitmap would be tighter but that can wait for the Rust port.

## why not `sequence <= last_seen`

Because packets arrive out of order. Example with window 5:

```
100 NEW, 101 NEW, 103 NEW, 102 NEW, 103 DUPLICATE, 104 NEW
```

102 is less than 103 but it was never seen, so it is NEW. The naive check would wrongly drop it.

## why exact dedup first

Bloom filters are the obvious next step for memory, but I want correct behavior pinned down first. This exact version becomes the ground truth to test the probabilistic one against later.

## still left to build

* Bloom filter or similar probabilistic prefilter in front of the exact window
* anomaly detection stage in the pipeline
* Rust / WASM port of the hot path
* buffering, retries, cloud upload
* any kind of UI

MQTT ingress above is just local mosquitto for learning. No real gateway features yet.

## MQTT setup (local mosquitto)

Install it:

* Windows: `winget install EclipseFoundation.Mosquitto` (or grab the installer from mosquito.org)
* Docker: `docker run -it -p 1883:1883 eclipse-mosquitto`

Start it:

```bash
mosquitto -v
```

It listens on port 1883 with no auth by default. That is fine for local tinkering.

## run the edge proxy

Needs Python 3.11+.

```bash
cd edge-telemetry-proxy
pip install -r requirements.txt
python -m src.mqtt_ingress
```

Options:

```bash
python -m src.mqtt_ingress --broker-host localhost --broker-port 1883 --topic "telemetry/#" --window-size 32
```

It prints one line per message, like `FORWARD device-00001 seq=42 (NEW)` or `DROP device-00001 seq=42 (DUPLICATE)`.

## run the publisher

In another terminal, with the broker and proxy running:

```bash
python simulator/mqtt_publisher.py --num-devices 5 --events-per-device 20
```

More knobs:

```bash
python simulator/mqtt_publisher.py --num-devices 10 --events-per-device 100 --duplicate-pct 0.1 --out-of-order-pct 0.05 --prefix telemetry --host localhost --port 1883 --seed 42
```

## example MQTT message

Topic: `telemetry/device-00001`

Payload (JSON):

```json
{"device_id": "device-00001", "sequence": 42, "timestamp": 1727740000.0, "metric": "temperature", "value": 21.5}
```

`device_id` in the payload is optional. If missing, the proxy takes it from the last part of the topic. `timestamp` and `metric` default too. `sequence` and `value` are required.

## Try it out (no MQTT path)

```bash
cd edge-telemetry-proxy
pip install -r requirements.txt
pytest tests/ -v
python benchmarks/benchmark_dedup.py
```

Benchmark defaults: 10,000 devices x 100 events, 10% dupes, 5% out of order, window 32. It prints totals for NEW / DUPLICATE / TOO_OLD, forwarded / dropped, reduction %, time and events per sec.

Small run:

```bash
python benchmarks/benchmark_dedup.py --num-devices 100 --events-per-device 50
```
