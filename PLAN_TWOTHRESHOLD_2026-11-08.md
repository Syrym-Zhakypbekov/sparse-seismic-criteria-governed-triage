# Plan (post hoc, method fixed before computing): two-threshold abstaining baseline, alert-threshold separation, total analyst items

Date: 2026-11-08. Written and pushed before any of the numbers below were computed. It answers points raised by the fair
internal review on v32: a comparator with its own reject band, the share of the alert gain that
comes from the fixed alert threshold θA rather than from the weight c, and analyst items when an automatic ALERT is also reviewed.
Descriptive; adds no hypothesis to the confirmatory family; frozen decisions and frozen pipeline outputs only.

Data: the 33 networks of the reviewed-bulletin analysis (Section 4.12), episodes and reviewed labels from
results/posthoc/_collect_reviewed.pkl (built by analysis/posthoc_collect.py), 6006 network-days.

1. Two-threshold P3 (P3-2t). ALERT if any neighbour YES and SNR ≥ tA; DISMISS if no YES and SNR < tD; otherwise ESCALATE;
   tD in 5.0–12.0 dB and tA in tD–20.0 dB, steps of 0.5 dB. P3 at 7.5 dB is the point tD = tA = 7.5 (self-check against the
   frozen P3 actions).
   - Frontier: for every point, pooled escalations per network-day, dismissed reviewed-associated alarms and automatic alerts
     without a reviewed event per network-day.
   - Matched comparison: among P3-2t points whose escalations per network-day are within ±5% of CG c = 0.5 (and of CG-D), the
     point with the fewest unassociated alerts subject to dismissing no more reviewed-associated alarms than CG c = 0.5
     (CG-D). Report that point and the difference with the cluster bootstrap of Section 3.6 (2000 resamples, seed 7).
2. Alert-threshold separation. CG with c = 0.5 and θA varied from 0.40 to 0.90 in steps of 0.05 (θD = 0.16, δ = 0.45 and all
   weights frozen; θA = 0.60 is the frozen point, self-check). Reported: escalations, dismissed reviewed-associated alarms and
   unassociated alerts per network-day, to show how much of the alert difference to P3 depends on θA.
3. Analyst items. For P1, P1t (8.0 dB), P3, CG, CG-D and CG c = 0.5: alerts + escalations per network-day (every item an
   analyst may look at if alerts are also reviewed), the share of those items that carry a reviewed event (queue precision),
   and dismissed reviewed-associated alarms. P1 is self-checked against the frozen actions; P1t is recomputed from its rule.

Output: analysis/posthoc_twothreshold.py, results/posthoc/twothreshold.json. Reported whatever the outcome.

## Addendum (written and pushed before computing, same day)
4. Cost sensitivity in which an automatic ALERT is also reviewed: analyst minutes per network-day = 2·escalations +
   a·alerts, with a = 0, 0.5, 1 and 2 minutes per alert, for P1, P1t (8.0 dB), P3, CG, CG-D, CG c = 0.5 and the matched
   two-threshold P3 points of item 1; computed only from the counts of items 1 and 3.
5. Blind adjudication package (planned, not yet adjudicated): the reviewed-associated episodes dismissed by CG c = 0.5 and
   not by P3, mixed with equal numbers of reviewed-associated episodes dismissed by both and alerted by both (seed 7),
   shuffled under neutral ids, waveform plots without rule labels; analysis/blind_adjudication_package.py, adjudication/blind_v1/.
   The key is kept separately. Adjudication by an analyst is future work and no result is claimed.
