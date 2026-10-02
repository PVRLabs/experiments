# Market replay fixture data

`data/quotes-2026-09-30.csv` contains one complete US regular-session trading
day: 390 one-minute close prices for AAPL, GOOG, and NVDA, from 09:30 through
15:59 America/New_York. The source was Yahoo Finance's chart data endpoint,
queried for the 2026-09-30 session on 2026-10-01. The checked-in CSV is the
only runtime data source; the fixture never contacts Yahoo Finance or any other
external service. Prices are stored to two decimal places. The companion
[`data/metadata.json`](data/metadata.json) records the source query and dataset
shape.

The data is historical market information supplied for a software experiment,
not investment advice. See the parent model-app README for replay semantics and
run instructions.
