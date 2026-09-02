# Failed constrained-VM follow-up checkpoints

After package-maintenance pressure had cleared, both JVMs started with JDK 25
and the same `Xmx80m` profile. At the three-minute checkpoint, 114 MiB was
available and 211 MiB of swap was used; Spring RSS was about 82 MiB and
Quarkus RSS about 140 MiB.

At approximately 11:40 PDT, the guest exhausted nearly all swap and the
kernel OOM-killed Spring. Spring restarted automatically and became healthy
again. Quarkus and StatLite did not restart. The final checkpoint had 85 MiB
available memory and 191 MiB swap used. Final endpoint checks returned HTTP
200, but Spring had one restart, so this remains failed operational evidence.

The selected `bounded-traffic.txt` and `kernel-tail.txt` preserve the direct
traffic and OOM evidence. The full service journal and database backup remain
private.
