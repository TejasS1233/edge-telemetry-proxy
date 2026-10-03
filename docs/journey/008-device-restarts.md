# 008 - Device restarts and boot_id

Date: 2026-10-03

## What I had

Dedup keyed on `(device_id, sequence)` with one window per device. Worked fine until I thought about what happens when a device reboots and its counter resets: `100, 101, 102, reboot, 0, 1, 2`. That fresh `0` is way below the old window, so the dedup would call it TOO_OLD and drop valid post reboot telemetry. Silent data loss on every restart, which for flaky field devices means a lot.

## The problem

Sequence numbers are only unique within one boot session, not across the device's lifetime. My identity key was missing a dimension. The fix had to distinguish sessions while keeping everything else identical: same window rules inside a session, old payloads without any session info still working.

## What I learned

The smallest correct change was making the key `(device_id, boot_id)` with `boot_id` defaulting to `""`. One run of the simulator is one session, so it just stamps the same id on everything, no random ids per event. MQTT carries it as an optional JSON field, missing means `""`, so old payloads land in the legacy session and behave exactly like before. `reset()` grew an optional second arg: device only clears all its sessions, device plus boot clears one.

## What changed

`Telemetry` and `DedupResult` gained `boot_id: str = ""`, dedup state is keyed per session, MQTT parse and encode roundtrip it, generator and publisher take `--boot-id`. 14 new tests, 41 total passing, benchmark numbers identical.

## Next

Anomaly detection stage in the pipeline. That is a whole new entry when it happens.
