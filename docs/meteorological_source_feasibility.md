# Bounded meteorological source feasibility

A development probe read Caravan-MultiMet v1.1 `ERA5_LAND` for six fixed gauges and two calendar windows: 2000-02-27 through 2000-03-02, and 2000-12-29 through 2001-01-02. Only precipitation and 2m temperature were selected. These are provider-derived catchment reanalysis values, not station observations or flood labels. Source: [Caravan-MultiMet methods and data availability](https://arxiv.org/html/2411.09459v1).

The captured metadata has 22,485 basin IDs and 27,333 daily date coordinates, from 1950-01-01 through 2024-10-31. All six exact `camels_<gauge>` coordinates occur once. A regular date axis does not establish complete values for every basin, and this source version does not cover the planned 2025 period.

| Gauge | Finite temperature cells | Finite precipitation cells | Unknown precipitation cells |
|---|---:|---:|---:|
| 01013500 | 10 | 10 | 0 |
| 02046000 | 10 | 10 | 0 |
| 05291000 | 10 | 10 | 0 |
| 06037500 | 10 | 10 | 0 |
| 09034900 | 10 | 0 | 10 |
| 10396000 | 10 | 0 | 10 |

Independent UTF-32 coordinate and binary float32 decoding reproduced all **100** selected values exactly. The 20 unknown cells belong to a retained partial object and an unrequested object; neither was decoded or filled with zero. Eight complete chunks each contain 3,498,624 float32 cells, or 13,994,496 uncompressed bytes. Their total per decoder is 27,988,992 cells / 111,955,968 bytes. Only the fixed cells were selected for numerical interpretation; most physical chunk storage is incidental.

The root metadata declares temperature in °C and precipitation in mm. This is a publisher-level unit declaration; individual arrays lack unit attributes. The captured arrays have no scale/offset transform. Treating these already processed values as raw ERA5 Kelvin/metres would apply an incorrect second conversion. For example, the source temperature for 01013500 on 2000-02-29 is 0.689788818359375 in its declared native units.

## Capture limitation

The ledger and retained bodies total **100,000,000 bytes**. A review found that the streaming client could read a fixed-size block and discard its surplus while recording only the saved prefix. Thus **the received-body cap is not established**. A disclosed constructed test reproduced uncharged overread; it did not measure the lost bytes of the actual transfer. The captured complete objects and selected values remain verifiable, but successful cap enforcement must not be claimed. No additional data requests are part of this review.

The source analysis remains incomplete. The authors describe daily UTC aggregation, but the captures do not establish exact interval endpoints or historical arrival. Root metadata, underlying ERA5-Land, original local-time Caravan processing and MultiMet UTC processing must remain distinguishable. Publisher data-license declarations exist; a stale embedded licence link is not evidence that the data has no licence. Version-specific attribution remains separate from repository-code licensing. No model, warning lead, population inference or full-study support is established.

## Candidate metadata and study-date envelope

An exact metadata-only crosswalk matches all 671 original CAMELS-US catalogue IDs once to `camels_<gauge>` coordinates: 671 matched, zero absent, zero ambiguous. Leading zeros and original catalogue fields are preserved. The JSON and CSV agree on all rows. This establishes coordinate membership, not current natural flow, statistical independence, cohort admission or finite forcing coverage.

The coordinate axis contains all 7,305 dates in the proposed 1990–2009 reference. Of 13,149 planned dates in 1990–2025, **426** fall after this source version's last coordinate: 2024-11-01 through 2025-12-31. These dates remain unsupported; the evaluation period has not been shortened to conceal that gap.

The candidate coordinates touch basin blocks 24–30. Access to both selected arrays would involve 14 chunk IDs, with 195,922,944 uncompressed bytes in total under the captured chunk geometry. This is a metadata-derived storage size, not a compressed download estimate. Unrequested compressed sizes and per-basin finite support remain unknown. No additional forcing values were read for this crosswalk.

Acquisition controls remain unapproved. Offline constructed tests exposed implicit redirect-body consumption in the HTTP library, admission after short file writes, missing-ledger recovery that ignores orphan bodies, and concurrent writers that can lose reservations. Those tests used no provider requests and do not alter the verified source values. A repaired client requires further review before any new acquisition.
