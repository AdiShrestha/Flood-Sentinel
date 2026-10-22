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
