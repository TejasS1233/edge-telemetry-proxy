# ADR-004 - MQTT ingress kept out of the pipeline

Date: 2026-10-02
Status: Accepted

## Decision

`src/mqtt_ingress.py` handles transport plus JSON parsing only. Dedup and forwarding decisions stay in `EdgePipeline`, untouched.

## Why

Mixing network code with dedup logic makes every parse bug look like a network bug and risks regressions in tested code. The hard line also keeps unit tests broker free: parsing and `handle_message` are tested with fake topics and payloads, no mosquitto needed.

## Alternatives considered

- Pipeline subscribes directly: fewer files, tangled responsibilities.
- Full gateway features (buffering, retries): too early, still learning.

## Consequence

Local mosquitto is dev only, no auth, no buffering or cloud upload. Those come later.
