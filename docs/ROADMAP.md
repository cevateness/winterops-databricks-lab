# Current roadmap — November 4, 2026

The charter defines stages, not deadlines. Historical execution evidence remains in its original reports; current product status is summarized here.

| Phase | Current result | Evidence / remaining boundary |
| --- | --- | --- |
| 0 — Source feasibility | Completed for the selected municipal files and historical weather interface | Pinned versions, contracts and licences recorded; future sources still require inspection |
| 1 — Data foundation | Four municipal weeks historically native-ingested and COMPLETE; three-week Gold historically published | Four-week Gold candidate reconciles locally. Native publication remains blocked by exact private approval inputs and secure access |
| **2 — Operational analytics** | **Completed as a local, reproducible historical MVP** | Actual interactive dashboard: four-week overview, equipment composition, day/hour recording patterns, coarse concentration, cached weather and UTC sensitivity. 298,051 observations reconcile; private detail rebuilt locally; no native dashboard deployment |
| 3 — Prediction | Not started | Requires the minimum information below; historical reanalysis is descriptive context, not decision-time forecast input |
| 4 — Decision analytics | Deferred | Requires useful predictions or explicit scenarios, actual capacity/crew/resource definitions and policy objectives |
| 5 — Portfolio release | Partly implemented | Public code, aggregate dashboard, tests, CI and reproduction guide exist; owner review and a clean release remain |
| Commercial exploration | Out of scope | No customer pilot, continuous service or commercial claims |

## Minimum entry conditions for Phase 3

1. **Decision and target:** specify prediction time, horizon, spatial unit and response variable. Future recorded observation count is a telemetry target; it is not automatically workload, service hours or coverage. Those outcomes need independent labels and definitions.
2. **Timestamp contract:** confirm the CSV exporter clock, DST/ambiguous-time behavior and late/revised-record treatment. Current January corroboration supports exploration, not a universal clock contract.
3. **Availability-aware features:** retain historical forecasts with issue time, valid time and availability/revision timestamps. Use only what existed at each prediction origin; later reanalysis/current-hour accumulations are unavailable future information for many decisions.
4. **Representative evaluation data:** more independent winter events/seasons, consistent observation cadence/equipment capture, known missing telemetry and stable source policies. Four weeks with activity-conditioned weather sampling are insufficient for credible out-of-time performance claims.
5. **Evaluation contract:** chronological event-separated training/validation/test, simple persistence/seasonal baselines, meaningful error/cost metrics and uncertainty. Do not randomly split correlated cell/hour observations or tune on the final events.

For service or resource targets, add actual duration/crew/equipment availability labels, contractor capture and, where relevant, road geometry and service standards. Native Gold publication is a separate platform milestone, not a reason to invent labels or skip leakage controls.

Next worthwhile task: owner review of the working dashboard and choice of one defensible analytical question/target. No model, extra provider, MLflow training, optimization or streaming infrastructure was added.

## Phase 2 extension — diagnostics V2

Implemented and executed reporting windows (1/5/15 minutes), heuristic episode sensitivity (15/30/60 minutes), known/unknown equipment transitions, sampled-weather associations and a separate private geographic playback view. Public diagnostics contain actual aggregate findings; private map browser QA is synthetic only. [Nine measured findings and their limits](OPERATIONAL_DIAGNOSTICS_V2_FINDINGS.md) include clock-sensitive and weak relationships. The original Phase 3 prerequisites remain unsatisfied. Next: owner review of exploratory findings and evidence needs, not automatic progression into modeling.
