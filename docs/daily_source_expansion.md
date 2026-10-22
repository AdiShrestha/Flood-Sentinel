# Daily discharge source-diversity probe

Six fixed CAMELS identifiers probe USGS daily mean discharge across HUC strings 01, 03, 07, 10, 14 and 17. Each is the first lexicographic catalogue ID in its HUC. This selection establishes neither representativeness nor independent river systems. All inspected values are exposed development data.

Five new stations each returned one compatible primary Daily Mean series (`00060/00003`, ft³/s). Records for 01013500 were reused as a control. The new captures used 60 nonoverlapping three-year queries over 1990–2025; every query ended without a next page. New response bodies, including metadata and five item checks, totalled 43,919,926 bytes under a prospective 100,000,000-byte cap. Ten failed DNS attempts remain separate from the successful provider responses.

Each station has 13,149 distinct returned dates, with one finite nonnegative value per date: 78,894 rows across the six stations. This establishes returned-date coverage, not intraday completeness or historical availability. The [source manifest](daily_source_expansion_manifest.json) binds the 63 daily response bodies, exact series, request URLs, sizes, hashes and quality counts. Raw responses are not included; source-specific redistribution terms require separate consideration.

| Site | Approved, unflagged | Approved, sole ESTIMATED | Approved, other qualifiers | Provisional | Q99 estimated retained | Q99 unflagged only |
|---|---:|---:|---:|---:|---:|---:|
| 01013500 control | 9,393 | 3,729 | 27 | 0 | 27062/3 | 143288/15 |
| 02046000 | 12,348 | 617 | 97 | 87 | 969 | 56729/60 |
| 05291000 | 9,110 | 3,989 | 50 | 0 | 17642/15 | 21191/15 |
| 06037500 | 12,695 | 432 | 22 | 0 | 24692/15 | 1670 |
| 09034900 | 9,776 | 3,321 | 9 | 43 | 6571/75 | 94 |
| 10396000 | 12,562 | 575 | 12 | 0 | 18871/25 | 77033/100 |

Q99 is an exact rational Type-8 diagnostic in ft³/s using only 1990–2009. That reference contains 7,305 dated rows per site; all are eligible when approved estimated values are retained. Unflagged reference counts are 5,235, 6,818, 5,139, 7,064, 4,824 and 7,022, respectively. These are real 20-calendar-year reference records. Whether a future study has adequate independent support remains unresolved.

The [date-only decoder](../source/flood_sentinel/usgs_daily_records.py) binds each record to its expected source identity, unit and date extent. It preserves missingness and ambiguous duplicates, distinguishes an absent qualifier from an explicit null, and returns rational quantiles. A separate raw parser and rational calculation reproduced all date/quality summaries and quantiles; raw-to-decoder comparison checked 1,104,516 fields. Seven original decimal quantile strings were approximations; their replacement fractions preserve the displayed values and produce no reference-value threshold classification changes. The original calculations remain historical diagnostics.

The [USGS migration guide](https://api.waterdata.usgs.gov/docs/ogcapi/migration/) documents date-only daily records. Current station metadata supplies EST/CST/MST/PST abbreviations and a daylight-saving flag; these do not authenticate historical series-specific UTC windows. [USGS statistics documentation](https://waterdata.usgs.gov/statistics-documentation/) explains daily summaries, without establishing complete within-day monitoring for these records. No new-site UTC intervals or labels are admitted. Release/arrival times, historical revisions, physical onset, warning lead, current regulation and network independence remain unknown.

Five same-provider item checks matched the captured properties and geometry while their top-level links differed. They establish neither historical vintages nor independent source authentication. A 2026 gage-datum revision note at 06037500 does not establish an effect on its historical discharge. No model performance or operational warning result is established. The earlier [three-station conditional aggregate analysis](daily_quality_feasibility.md) remains a separate development analysis.
