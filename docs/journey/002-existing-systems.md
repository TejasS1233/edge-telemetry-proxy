# 002 - Existing systems reality check

Date: 2026-10-01

## What I had

Coming out of 001 I had a sketch and a suspicion that I might be reinventing the wheel. So I went and read what the big players actually ship.

## The problem

The docs I read:

- AWS IoT SiteWise Edge MQTT gateway (collects, buffers, forwards sensor data at the edge)
- Azure IoT Edge LoRaWAN starter kit

Plus a bunch of first party stuff from MQTT providers and Bloom filter writeups, which I highly recommend reading if ur into this.

And yeah, the individual pieces all exist. Gateways collect MQTT, buffer offline, forward upstream. Nothing about my sketch was new at the component level.

## What I learned

The interesting bit was not "I found SiteWise" but what it forced me to change. What I thought vs what is actually different:

- I thought edge side dedup was the novel idea. It is not, gateways already do buffering and basic filtering.
- What existing gateways mostly do is path/topic filtering and store and forward. Stateful per device sequence tracking with explicit NEW / DUPLICATE / TOO_OLD semantics is not the standard story.
- So I reframed the project. It is not "a new gateway". It is an investigation into stateful dedup plus adaptive filtering plus collaborative validation later, with actual measured tradeoffs.

Also one honest note: I didnt really like the path filters part in the gateway docs. Felt like there is tons of scope in it and ill prolly try my own take on it at some point.

## What changed

I stopped claiming novelty and started claiming a combination: exact dedup ground truth first, then probabilistic filtering, then anomaly detection, measured at each step. That is the actual project now.

## Next

Build the smallest thing that proves the core: a Python dedup prototype with real semantics, no networking yet.
