# Memory-residency checkpoints

These values summarize the selected `/proc` snapshots from the private
memory-residency follow-up. The detailed interpretation is in the journal.

| Checkpoint | Spring RSS | Quarkus RSS | Spring JVM heap | Quarkus JVM heap | Spring VmSwap | Quarkus VmSwap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Settled | 114308 KiB | 148016 KiB | 43.6 MB | 28.0 MB | 100.4 MiB | 28.8 MiB |
| 60 minutes | 157808 KiB | 85448 KiB | 50.3 MB | 33.1 MB | 66.0 MiB | 90.9 MiB |

Spring's resident and proportional footprints rose over the follow-up. Quarkus
RSS and PSS fell while its JVM heap grew and its swap residency increased.
This supports paging as an important part of the apparent RSS advantage.
