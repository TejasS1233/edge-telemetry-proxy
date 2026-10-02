# 001 - The idea

Date: 2026-10-01

## What I had

Just a vague problem statement really. IoT devices spam telemetry nonstop, and a lot of what reaches the cloud is redundant. Retries, flaky networks, sensors reporting the same reading over and over. So the question was simple: what if a little box at the edge dropped the repeats before they ever left the site.

My initial sketch was literally this:

```
Device
  |
Edge Proxy
  |
Deduplication
  |
Cloud
```

That was it. No details, no idea how dedup would actually work, just the shape of it.

## The problem

At this point I did not know if the idea was useful or novel or neither. Edge gateways already exist, MQTT brokers already exist, so for all I knew I was reinventing smth that ships by default. I also had no clue what "duplicate" even means for sensor data. Same reading twice in a row, is that a dupe or just a stable sensor? Retried packet with the same id, that one is clearly a dupe. I was mixing both up.

## What I learned

That the problem needs splitting before any code. There are two different things: exact duplicates (same packet arriving twice because of retries) and redundant readings (new packet, same value). The first one is solvable with packet identity alone and never destroys real data. The second one needs value logic and thresholds, which is way more opinionated. So I decided to start with exact duplicates only and leave the rest for later.

## What changed

The project got its first boundary: this repo handles exact packet-level dedup at the edge, nothing else for now. No anomaly stuff, no value filtering, no cloud side. That one decision made everything after it simpler.

## Next

Reality check. Before writing code I need to see what AWS and Azure already do here, so I dont go build a worse version of a solved problem.
