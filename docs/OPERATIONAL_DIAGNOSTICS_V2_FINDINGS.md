# Operational diagnostics V2 — measured findings

Executed November 4, 2026, from the four exact pinned CSV versions and the existing hash-verified weather archive. No new source/weather downloads or Databricks calls. All 298,051 VALID observations remain in every reporting-width and episode-gap alternative. [Machine-readable results](../dashboard/diagnostics.json) · [execution receipt](OPERATIONAL_DIAGNOSTICS_V2_EXECUTION.json) · [interactive diagnostics](../dashboard/diagnostics.html).

These are descriptive associations in an activity-triggered, four-week sample. Supporting tables below correspond to named result arrays in `diagnostics.json`; dashboard sections expose the same results. Counts of identifiers in a window are reporting overlap, not instantaneous service or availability. Episode onsets are first observations, not dispatches.

## 1. Peak reporting is nearly stable across window widths, but its time changes

| Window | Occupied windows | Maximum distinct reporting IDs | First source-local occurrence of the maximum |
| --- | ---: | ---: | --- |
| 1 minute | 12,497 | 17 | January 14, 18:09 |
| 5 minutes | 2,835 | 18 | January 16, 16:15 |
| 15 minutes | 1,067 | 18 | January 16, 16:15 |

**Unit/denominator:** one occupied source-local reporting bucket; identifiers are deduplicated inside it while observation counts are retained. Support: `reporting[grain=week]`, dashboard §1. Peak magnitude survives the 5/15-minute comparison, but timestamp and the one-minute maximum differ. Weather timezone hypotheses do not change source-clock reporting counts. The wider window can combine identifiers that never reported at the same instant. These are first maxima, not necessarily unique peaks.

## 2. Recording intensity differs substantially across weeks

| Source week | Occupied 5-minute windows | Mean reporting IDs | Median | P95 | Peak |
| --- | ---: | ---: | ---: | ---: | ---: |
| January 5 | 183 | 1.03 | 1 | 1 | 2 |
| January 12 | 755 | 7.32 | 7 | 15 | 18 |
| January 19 | 1,044 | 6.49 | 5 | 14 | 17 |
| January 26 | 853 | 5.63 | 5 | 13 | 16 |

**Unit/denominator:** occupied 5-minute buckets within each selected source week. Support: `reporting`, daily bars and hour-of-day table, §1. The first week's maximum stays 2 at all three widths; the other weeks' peaks are 16–18. This survives clock choice, but cannot be called a fleet-size or demand trend: recording completeness/cadence and activity-triggered selection differ. No absent bucket is inserted as zero reporting.

## 3. Episode counts are highly sensitive to the gap definition

| Maximum gap | Observed episodes | Source-first episodes | Episodes following a recording gap | One-timestamp episodes |
| --- | ---: | ---: | ---: | ---: |
| 15 minutes | 1,578 | 817 | 761 | 68 |
| 30 minutes | 1,202 | 817 | 385 | 41 |
| 60 minutes | 989 | 817 | 172 | 28 |

**Unit/denominator:** all observed episodes under each alternative segmentation; each separately contains 298,051 observations. Support: `episodes`, `episode_timing`, §2. Moving from 15 to 60 minutes reduces the count by 589 (37.3% of the 15-minute count). At the reference threshold, 817/1,202 (68.0%) begin with the first record for that identifier/source scope. These are 817 identifier/source combinations, not 817 distinct vehicles. All actual operational starts/ends are censored. Apparent spans remain source-clock spans and cannot be added into work hours. Clock choice does not change this January segmentation; the gap threshold clearly does.

## 4. Conservative transition handling materially changes the answer

| Continuity limit | Known consecutive timestamp intervals | State changes | Gap-unknown entries | Conflicting-tie-unknown entries |
| --- | ---: | ---: | ---: | ---: |
| 15 seconds | 250,109 | 17,251 | 33,371 | 6,779 |
| 60 seconds | 276,657 | 18,202 | 6,455 | 7,147 |
| 300 seconds | 281,211 | 18,478 | 1,886 | 7,162 |

**Unit/denominator:** consecutive timestamp-group entries within identifier/source; each scenario additionally has 817 source-first unknown entries. Known intervals include same-state persistence. Support: `transitions`, §3. The 60-second state-change rate is 18,202/276,657 = 6.58%; known flag activations comprise 2,560 plow and 7,138 spreader changes (a transition can activate a flag without representing a new dispatch). Unknown categories are mutually exclusive, with gap exclusion taking precedence over a conflicting endpoint. Counts are continuity-sensitive; no transition or activation crosses a rejected gap/tie. Weather clock choice has no effect on these source-clock statistics.

## 5. Ties and repeated payloads are meaningful data-quality constraints

There are **291,076 truck/timestamp groups**, **6,975 extra observations at tied timestamps** (2.34% of 298,051 observations), and **3,779 groups with contradictory equipment states** (1.30% of timestamp groups). The established Gold definition flags **3,981 observations in repeated valid-payload groups** (1.34%); this is not the same as excess duplicates or tied timestamps.

**Unit/denominator:** observations or truck/timestamp groups as explicitly stated. Support: `quality`, §6; unchanged V1 Gold quality output. Grouping equal timestamps avoids inventing an order among conflicting states. Multiplicity stays in all counts; only state-transition certainty is withheld. Findings 1–3 still reconcile without deleting these records. This diagnostic is independent of weather clock and episode threshold; its effects on transitions depend on the continuity rule.

## 6. A pooled snowfall/reporting association is not consistent within every week

Across **325 occupied source hours**, correlating mean sampled snowfall with the mean reporting-ID count across occupied five-minute windows gives descriptive Pearson **r=0.423 under Toronto** and **r=0.552 under UTC**. Those source hours contain **842 sampled grid/hour windows** per hypothesis; they are not independent experimental observations.

| Source week | Occupied source hours | Toronto r | UTC r |
| --- | ---: | ---: | ---: |
| January 5 | 42 | 0.002 | 0.017 |
| January 12 | 79 | 0.351 | 0.669 |
| January 19 | 115 | 0.553 | 0.600 |
| January 26 | 89 | −0.195 | 0.313 |

**Unit/denominator:** one source hour, pairing unweighted distinct-grid weather means with its mean reporting count. Support: `relationships.continuous`, §4 scatter; choose week, five-minute window and snowfall. The pooled positive direction survives clock choice, but the fourth week's sign does not. Week mix, storm timing, serial dependence and observation selection matter. Temperature's pooled r is weakly negative (−0.146 Toronto, −0.126 UTC). No significance, exposure-adjusted deployment probability or causal claim is supported.

## 7. Some equipment/weather contrasts survive clock choice; warm-category contrasts do not

Toronto positive-snowfall cell/hours have **47.36% spreader-active observations** (147,834 total observations over 296 cell/hours), versus **38.09%** for zero-snowfall samples (150,217 observations over 546 cell/hours). Under UTC, the corresponding shares are **47.57% versus 33.27%** (338 versus 504 cell/hours). The direction survives the clock sensitivity; magnitude and cohort membership change.

However, the **T ≥ 0°C** spreader-active share changes from **14.74% under Toronto** (4,172 observations; 88 cell/hours) to **50.35% under UTC** (13,553 observations; 106 cell/hours). That comparison is not robust enough for an operational explanation. Below −10°C, shares are much closer: **25.11% versus 24.74%** (319 versus 306 cell/hours).

**Unit/denominator:** activity cell/hour cohorts, with the quoted equipment shares weighted by retained observation counts, not independent pings in a significance test. Support: `relationships.cell_hour`, §4; each row also gives distinct weather-fact and source-hour support. Continuous values are not rounded before categorizing. These are sampled equipment compositions, not service effectiveness or salt policy compliance. Existing seasonal policy pages do not establish January practices.

## 8. Half the reference episode onsets have positive sampled prior snowfall—but that is not deployment probability

At 30 minutes, Toronto has **601/1,202 observed onsets (50.0%)** with positive prior two-hour snowfall and 601 with zero. UTC yields **619/1,202 (51.5%)** positive and 583 zero; missing onset weather is zero in this actual archive. Prior precipitation is positive for **614/1,202 Toronto** and **640/1,202 UTC**.

**Unit/denominator:** observed episode onsets, not all potential deployment occasions. Support: `relationships.episode_onsets`, §4. Antecedent intervals end at the containing-hour start; the partial onset hour is excluded. Several episodes can share the same weather facts; the table reports distinct fact/window support. Broad positive/zero balance survives clock choice, but the underlying episode cohort changes with gap threshold (see §3). Without non-activity weather exposure periods and independent dispatch labels, these fractions cannot estimate deployment likelihood.

## 9. Concentration shifts are descriptive, and coarse resolution limits interpretation

The two largest existing coarse cells contain **56.72%, 88.13%, 89.69% and 91.56%** of weekly observations, respectively, using the V1 public map and full weekly observation denominators (2,791; 110,311; 118,125; 66,824). These percentages are time-interpretation independent. Public map withholding remains 12 observations in small cell/week groups; no record is dropped from complete analytical products.

**Unit/denominator:** fixed 0.25° cell/week observation totals, not road length or serviced area. Support: V1 `cells` and `weekly`; private playback shows the corresponding hour/equipment context without publishing those intersections. The first week is much smaller and contains 677 of the 863 outside-review observations, so its spatial distribution is not comparable as a coverage outcome. Coarse cells can span many roads and regional context outside Windsor; there is no road-coverage denominator.

## What would improve interpretation

A bounded calendar of independent weather exposure hours would help describe weather outside the activity-conditioned sample, but would still need verified clock alignment, retrieval provenance, clear missingness and an exposure definition. It would not create dispatch labels. The official snow-plowing/salting 311 request feed could add independently generated complaint timing, subject to duplicate complaints, changing YTD extracts and unresolved event-time semantics; it does not provide verified road completion. Research details and access/licensing boundaries are in [the technical review](OPERATIONAL_DIAGNOSTICS_V2.md). Nothing new was integrated or collected.
