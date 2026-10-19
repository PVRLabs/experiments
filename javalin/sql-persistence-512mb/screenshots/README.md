# Monitored MyBatis run: article screenshots

Original operator-supplied PNGs, preserved without editing, from monitored run
`20261019T215517Z-javalin-mybatis` on 2026-10-19. The dashboard used the one-hour
view. Exact capture times are not recorded; both images include post-cutoff
inspection. The measured workload ran 14:57:51–15:02:51 PDT, with measurement
cutoff at 15:03:21 PDT (22:03:21 UTC).

## StatLite self-monitoring

File: [statlite-self-monitoring.png](statlite-self-monitoring.png)

Suggested caption: StatLite self-monitoring during the MyBatis follow-up,
showing its runtime memory and process CPU alongside guest RAM, host CPU and
disk usage. The displayed history spans approximately 14:55–15:05 PDT, including
monitor-only baseline, application execution and post-cutoff inspection.

Alt text: StatLite dashboard charts showing self-target average latency,
runtime memory and process CPU, plus guest memory, CPU and disk usage.

Runtime memory is the reported runtime metric, not process RSS. The small
runtime-memory values and their drop must not be interpreted as equivalent
changes in the monitor's resident memory. Independent OS sampling supplies RSS.
The screenshot does not contain the target selector; the operator identified
this view as the StatLite self-target.

## Javalin MyBatis process monitoring

File: [javalin-mybatis-monitoring.png](javalin-mybatis-monitoring.png)

Suggested caption: The Javalin MyBatis target during the monitored five-minute
workload, showing request counts per polling interval, HTTP errors, average
latency, runtime memory and process CPU. Status cards reflect post-run inspection;
the last successful poll shown is 15:04:18 PDT.

Alt text: StatLite dashboard for javalin-mybatis with UP status, zero poll
failures, request traffic falling after the workload, zero HTTP errors, average
latency and runtime-memory/process-CPU charts.

The displayed DB health is "Not reported"; application UP is not an explicit
database-health result. Final database correctness was checked independently.
Runtime memory is a JVM runtime/heap metric, not RSS, and average dashboard
latency is not the external workload p95. Chart interpolation is presentation,
not evidence of additional samples between 30-second polls.
