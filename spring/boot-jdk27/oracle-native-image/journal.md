# Oracle native curation journal

**Status:** Accepted Oracle data curated and reanalysis verified for publication.
**Next action:** Use the reproduction guide to inspect or recheck the evidence.

## 2026-10-28 — Validate and curate the Oracle follow-up

The accepted native deployment completed functional checks, two preparation
smokes and one measured 60/120/300/60-second run. Preparation is excluded from
measurements. The separate builder and runtime budgets, JDK 25 native versus
JDK 27 HotSpot baseline, OS patch drift and single-run limits are retained in
[the method](README.md) and [reproduction guide](reproduction-guide.md).

Regenerated all 43 candidate files byte-for-byte from the source archive and
verified the historical F snapshot against the published GitHub dataset.
Published only curated source, fixture, configuration, sample/request projections,
compiler excerpt and accepted summaries. Added comparison/snapshot consistency
checks and clarified CSV projection guidance; no measurements changed. Both
native and existing HotSpot reanalysis passed. Live functional/compiler/startup
observations remain retained evidence, rather than independently replayed checks.
