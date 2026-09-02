# Controlled comparison checkpoints

The health-enabled 2026-09-01 run is the authoritative controlled comparison.
The selected final checkpoint recorded 452 MiB guest-visible RAM, 221 MiB
swap used, Spring RSS 62956 KiB, Quarkus RSS 159740 KiB, StatLite RSS 14208
KiB, and combined RSS 236908 KiB. All final endpoint checks returned HTTP 200
and systemd reported zero restarts for the three services.

The run was qualified because both applications independently polled the live
unauthenticated GitHub API and reached its per-IP rate limit during the hour.
The applications continued running and recovered when the limit window
cleared. See `preflight.txt`, `final-target-summary.json`, `bounded-traffic.txt`,
and `kernel-tail.txt` for the preserved supporting evidence.
