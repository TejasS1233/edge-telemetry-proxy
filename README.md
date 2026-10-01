# edge-telemetry-proxy

A prototype for an edge box that sits between IoT devices and the cloud, drops duplicate telemetry locally, and only forwards fresh stuff upstream.

Im basically trying out ideas for something like the AWS IoT SiteWise Edge MQTT Gateway. That thing collects, buffers and forwards sensor data at the edge and yes ik realistically its all wasm and rust BUT this is just a sort of conceptual understanding.

Things I have read till now and u can too if you are interested: 
- https://docs.aws.amazon.com/iot-sitewise/latest/userguide/mqtt-enabled-v3-gateway.html
- https://azure.github.io/iotedge-lorawan-starterkit/dev/quickstart/

personally I didnt really like the path filters part , i think there is tons of scope in it and ill prolly think of a way to implement smth

Also read many articles on from like the first party(mqtt providers and bloomfilter articles etc HIGHLY recommend reading)
personally I didnt really like the path filters part , i think there is tons of scope in it and ill prolly think of a way to implement smth

## Architecture

Right now it is pretty simple:

```
devices -> EdgePipeline -> dedup check -> FORWARD or DROP -> upstream (later)
```

Files:

* `src/telemetry.py` - the event shape: device_id, sequence, timestamp, metric, value
* `src/dedup.py` - per device sliding window dedup, returns NEW / DUPLICATE / TOO_OLD
* `src/pipeline.py` - NEW means FORWARD, everything else means DROP. Has an `add_stage()` hook so anomaly detection can plug in later
* `src/config.py` - workload settings
* `simulator/generator.py` - fake devices with dupes, out of order and late packets
* `benchmarks/benchmark_dedup.py` - load test + stats
* `tests/test_dedup.py` - pytest suite

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


* MQTT broker / gateway ingress (the real SiteWise style entry point)
* Bloom filter or similar probabilistic prefilter in front of the exact window
* anomaly detection stage in the pipeline
* Rust / WASM port of the hot path
* buffering, retries, cloud upload
* any kind of UI

## Try it out!

Needs Python 3.11+.

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
