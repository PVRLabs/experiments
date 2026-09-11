# Primary comparison result

The twelve-run raw archive remains private. Values below are the final public
summary; time is seconds except external startup (milliseconds), RSS, and swap
(KiB).

| run | layout | Spring startup | external startup | first request | request 2 | request 3 | request 4 | request 5 | request 6 | peak RSS | settled RSS | swap delta | stable |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 01 | fat | 10.477 | 11270 | 1.981374 | .204841 | .018290 | .015562 | .024877 | .023107 | 161448 | 145304 | 145258 | yes |
| 02 | extracted | 8.993 | 9560 | 1.504225 | .205573 | .018523 | .016346 | .017250 | .016221 | 151504 | 130544 | 140512 | yes |
| 03 | extracted | 8.897 | 9480 | 1.656602 | .233927 | .044585 | .016510 | .017918 | .021028 | 157500 | 136540 | 130804 | yes |
| 04 | fat | 11.284 | 12140 | 2.436299 | .236098 | .047235 | .029986 | .043949 | .027133 | 160136 | 140940 | 145436 | yes |
| 05 | fat | 11.030 | 11900 | 2.332848 | .201574 | .017649 | .014009 | .015984 | .019982 | 159992 | 132436 | 147076 | yes |
| 06 | extracted | 8.029 | 8560 | 1.354330 | .144077 | .024811 | .015957 | .017198 | .014417 | 154960 | 130116 | 134792 | yes |
| 07 | extracted | 8.100 | 8630 | 1.365086 | .116943 | .020529 | .039767 | .035301 | .015467 | 160848 | 133360 | 143560 | yes |
| 08 | fat | 11.082 | 11920 | 2.087719 | .195561 | .025382 | .018094 | .020475 | .021992 | 153088 | 132316 | 145080 | yes |
| 09 | fat | 11.004 | 11820 | 1.946922 | .161856 | .021038 | .017857 | .019399 | .015184 | 165272 | 138664 | 143116 | yes |
| 10 | extracted | 8.591 | 9110 | 1.490406 | .174063 | .028982 | .016439 | .015958 | .015810 | 156180 | 127916 | 141376 | yes |
| 11 | extracted | 8.361 | 8890 | 1.405012 | .065044 | .017200 | .017170 | .021894 | .029440 | 154208 | 139364 | 127528 | yes |
| 12 | fat | 11.560 | 12490 | 2.303610 | .216075 | .016686 | .019307 | .034265 | .017122 | 158408 | 135760 | 155188 | yes |

| metric | fat median | extracted median | extracted minus fat |
|---|---:|---:|---:|
| Spring startup | 11.056 s | 8.476 s | -23.3% |
| External startup | 11910 ms | 9000 ms | -24.4% |
| First request | 2.195665 s | 1.447709 s | -34.1% |
| Median requests 2–6 | 0.020696 s | 0.019139 s | -7.5% |
| Peak RSS | 160064 KiB | 155570 KiB | -2.8% |
| Settled RSS | 137212 KiB | 131952 KiB | -3.8% |
| Swap delta | 145347 KiB | 137652 KiB | -5.3% |

Conclusion: extracted materially improved startup and first request in this
setup. No material later-request or memory/swap winner was observed.
