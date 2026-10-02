# 006 - Adding MQTT ingress

Date: 2026-10-02

## What I had

A working pipeline that only ate in process Python objects from the simulator. Fine for algorithms, useless for learning how edge systems actually ingest data. The SiteWise style gateway reads from MQTT, so the proxy should too.

## The problem

Two new things to get right at once: the transport (broker, topics, subscribe) and the translation (JSON bytes on the wire into my clean `Telemetry` object). If I mixed them together, every parse bug would look like a network bug. Also I did not want to touch the dedup algorithm at all. It was correct and tested, and "while Im here" edits are how regressions happen.

## What I learned

Keeping a hard line between ingress and pipeline made everything easy. `src/mqtt_ingress.py` does transport plus parsing only: subscribe to `telemetry/#`, decode JSON, build `Telemetry`, hand it to the untouched `EdgePipeline`. Device id falls back to the last topic segment if the payload omits it, and junk payloads log and get counted as drops instead of crashing the loop. The publisher (`simulator/mqtt_publisher.py`) reuses the same generator as the benchmark, so the traffic mix is identical, just delivered over a real broker.

Also learned: unit tests must not need a broker. All the parse and convert tests use fake topics and payloads, and `handle_message` is tested directly with no network. If tests needed mosquitto running, nobody would run them.

## What changed

New modules `src/mqtt_ingress.py` and `simulator/mqtt_publisher.py`, plus `MqttConfig` for host/port/topic. Dedup, pipeline decisions and benchmark behavior are unchanged. 10 new tests, 27 total passing.

## Next

Benchmark properly and write down real numbers: throughput, reduction rate, scaling with device count. Then decide if the set based window survives contact with bigger loads.
