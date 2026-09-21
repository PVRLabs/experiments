# 768 MiB vs 1 GiB comparison

The 1 GiB follow-up used the same applications, JVM flags, startup order,
fixture, workload, and six observation points as the 768 MiB run. The VM showed
955 MiB guest-visible RAM and `Swap: 0B` throughout the follow-up.

RSS values below are MiB. Heap values are bytes and remain contextual because
normal garbage collection changes them between snapshots.

| checkpoint | Spring RSS: 768 MiB | Spring RSS: 1 GiB | Quarkus RSS: 768 MiB | Quarkus RSS: 1 GiB |
|---|---:|---:|---:|---:|
| ready-pre-request | 228.2 | 233.1 | 164.6 | 169.6 |
| after-one-request | 223.9 | 234.8 | 163.8 | 170.5 |
| post-workload | 221.3 | 235.4 | 164.4 | 171.9 |
| intermediate | 210.1 | 239.7 | 172.1 | 178.4 |
| mid-5m | 208.3 | 240.0 | 173.5 | 179.6 |
| after-10m | 202.3 | 240.4 | 175.7 | 181.2 |

The 768 MiB run had Spring process swap rising to about 34.3 MiB and Quarkus
process swap at zero. With swap disabled at 1 GiB, both applications recorded
zero process swap. RSS was higher in the 1 GiB run for both applications,
especially Spring late in the observation; that is an observed RSS difference,
not evidence that the extra memory made either application intrinsically more
or less efficient.

Spring and Quarkus completed ten HTTP 200 workload requests each, remained
active with zero restarts, and StatLite reported zero consecutive poll failures
for all three targets at closeout.
