# Results

## Checkpoint comparison

RSS and swap are process values in KiB. Heap values are in bytes and are the
non-GC heap values captured with `jcmd`; they fluctuate with normal garbage
collection and are reported as context rather than used alone to rank the
applications.

| checkpoint | Spring RSS | Spring swap | Spring heap | Quarkus RSS | Quarkus swap | Quarkus heap |
|---|---:|---:|---:|---:|---:|---:|
| ready-pre-request | 233676 | 0 | 2705408 | 168540 | 0 | 7708672 |
| after-one-request | 229252 | 4564 | 16827392 | 167748 | 0 | 1784832 |
| post-workload | 226656 | 7776 | 21201920 | 168304 | 0 | 5255168 |
| intermediate | 215188 | 25940 | 20635648 | 176260 | 0 | 8192000 |
| mid-5m | 213332 | 28268 | 7501824 | 177676 | 0 | 3303424 |
| after-10m | 207156 | 35152 | 13649920 | 179936 | 0 | 8652800 |

Spring remained above Quarkus in RSS at every checkpoint and accumulated about
34 MiB of process swap by the final checkpoint. Quarkus accumulated no process
swap. StatLite RSS remained approximately 15–21 MiB.

## Workload and health

- Spring workload requests: 10
- Quarkus workload requests: 10
- Workload responses: HTTP 200 for every request
- Spring and Quarkus restarts: 0
- StatLite target poll failures at closeout: 0
- Fixture requests: 15 repository requests and 7 health requests
- SQLite integrity check: `ok`

The final host-memory gauge was 605,777,920 of 737,714,176 bytes. The final
StatLite dashboard showed both applications healthy and polling successfully.

## Conclusion

For this workload and constrained VM, Quarkus had lower resident memory and no
process swap, while Spring had higher resident memory and increasing swap
pressure. Both applications remained operational during the ten-minute
observation.

## 1 GiB no-swap follow-up

The same applications, JVM profile, fixture, workload, startup order, and
checkpoints were repeated after changing the VM to 1 GiB and running
`sudo swapoff -a`. Guest-visible memory was 955 MiB and swap remained `0B`.

At the ten-minute checkpoint, Spring RSS was 240.4 MiB and Quarkus RSS was
181.2 MiB. Both recorded zero process swap. In the original 768 MiB run, final
RSS was 202.3 MiB for Spring and 175.7 MiB for Quarkus, while Spring had
accumulated 34.3 MiB of process swap. The higher 1 GiB RSS values are observed
RSS differences under different memory pressure, not a standalone efficiency
ranking. Heap values also varied with normal GC and remain contextual.

Both applications completed ten HTTP 200 workload requests, had zero restarts,
and StatLite reported zero consecutive poll failures for all three targets.
See the [follow-up comparison](results/follow-up-1g/comparison-768-vs-1g.md)
and [follow-up checkpoints](results/follow-up-1g/checkpoints.csv).
