# Conditional six-site aggregate and input support

This exposed development replay uses the [six-site daily source capture](daily_source_expansion.md) and its [manifest](daily_source_expansion_manifest.json). It adds no new daily-data requests. The 63 decoded daily bodies total **52,599,228 bytes**. The larger 52,640,858-byte retained capture includes metadata and item checks as well. Returned dates, historical publication and intraday completeness are different properties.

The analysis retains all six catalogue-first stations, daily noon UTC issues during 2010–2025, elapsed 24/48/72-hour horizons and four combinations of reference/truth quality. Reference Q99 uses exact rational Type-8 interpolation on 1990–2009 only. The target remains the [daily aggregate-completion definition](daily_quality_feasibility.md): three usable low/equal days arm, a strict-above-threshold aggregate completes and disarms, and missing/unusable support remains explicit. These are daily-aggregate labels, not physical flood-onset observations.

Civil clock assumptions are New York for 01013500/02046000, Chicago for 05291000, Denver for 06037500/09034900, and Los Angeles for 10396000. Matching fixed UTC−05/06/07/08 alternatives provide clock sensitivity. Saved IANA 2026e rearguard rule files define these scenarios; they do not authenticate historical USGS aggregation intervals. Civil days include 23/25-hour intervals. All assigned closures precede noon, so both scenarios select the same date sequence and target status/record lineage while verification times can change.

Each clock scenario has 420,768 target rows: **369,329 negative, 1,936 positive and 49,503 unknown**. There are 777 lane-specific completions per scenario over 1990–2025, including reference-period episodes. Restricting completing source dates to 2010–2025 gives 329 lane-specific completions and **99 distinct station/source-record pairs** across policies. Neither quantity is an independent flood count.

Future completion IDs can remain diagnostic fields on unknown rows. Across both clock scenarios, 3,872 such references occur on positive rows and **76 on unknown rows**. Counting every reference as a positive would be wrong. For example, 02046000 at 2025-07-18 12:00Z, 72 hours, is recovering and remains unknown even though the future record `3716fb3e-7a21-4968-b899-e739fa3908be` has an assigned completion within the horizon.

## Input information support

For each clock/delay, all 35,064 station/issues remain. Only approved unflagged finite discharge enters inputs. The latest expected day must satisfy assigned closure plus a hypothetical elapsed-UTC delay ≤ issue; an unusable latest value is masked rather than replaced by an older one. A 365-calendar-day history ends on that expected day.

| Hypothetical delay | Usable latest values | Masked latest values | Observed history-day exposures | Masked history-day exposures |
|---:|---:|---:|---:|---:|
| 0 h | 29,784 | 5,280 | 10,899,031 | 1,899,329 |
| 24 h | 29,785 | 5,279 | 10,899,050 | 1,899,310 |
| 48 h | 29,786 | 5,278 | 10,899,066 | 1,899,294 |

The table applies separately to each clock scenario. Histories overlap heavily; these are repeated day exposures, not new observations. No issue has zero observed history days, but the longest masked run is 153 days. The initial narrative incorrectly repeated the zero-delay history totals for every delay; the underlying rows and detailed support tables contain the differing values above. No prediction comparison establishes that these delays are harmless.

## Verification and limits

A separate raw implementation reproduced all **841,536 target rows, 210,384 input rows and 1,554 completion-ledger rows** with no differences. Detailed verification also checked 14,420 target support cells, 2,304 input support cells, 24 exact threshold summaries and 70,128 matching control rows from the earlier three-station analysis. The nine constructed boundary tests pass. Preserved pre-summary-repair target/input streams have identical decompressed content to the corrected replay. These checks establish computational consistency under the stated assumptions.

Historical vintages, release/arrival times, provider-specific daily intervals, physical onset/lead, current regulation and network independence remain unknown. A delay added to current final-product data does not undo later revisions. A strict one-day input has a different information budget from an annual-history or multichannel model. No model, training improvement, population inference or operational warning result is established.
