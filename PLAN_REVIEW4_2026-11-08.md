# Plan (post hoc, written before computing): review4 — answers to the final internal review of v33 (afb1eb0)

Data: the 33 reviewed-bulletin networks (results/v2_reviewed), frozen rule v2 (W_RANK 0.25/0.20/0.15, W_SNR 0.40,
theta_A 0.60, theta_D 0.16), pooled two-stage cluster bootstrap (2000, seed 7), margin 3 points. Descriptive, post hoc.

1. delta_sweep (M2). Replace delta = 0.45 by 0.45, 0.55, 0.60, 0.65, 0.75, 0.85, 0.95 (all else frozen) for CG (c = 1),
   CG c = 0.5 and CG-D. Report per value: decisions changed vs frozen, reviewed-associated dismissals, escalations,
   unassociated alerts, all dismissals; and the first delta at which reviewed-associated decisions change.
2. dev_two_threshold (M3). Two-threshold abstaining rule P3-2t (dismiss if no YES and SNR < tD, alert if any YES and
   SNR >= tA, escalate otherwise; tD in 5.0..12.0, tA in tD..20.0, step 0.5). Setting chosen on the TRAINING networks
   only (batch A, results/v2/networks.json, reviewed labels): escalations within +-5% of CG c = 0.5 on training and no
   more reviewed-associated dismissals than CG c = 0.5 on training; among these the fewest unassociated alerts
   (if none: the setting closest in escalations). Evaluated on the batch-B test networks among the 33 (not used to
   choose) and, secondary, on all 33: reviewed-associated dismissals (cluster bootstrap CG c = 0.5 and CG-D minus
   P3-2t), unassociated alerts, escalations, alerts + escalations.
Output: results/review4/delta_sweep.json, results/review4/dev_two_threshold.json. Reported whatever the outcome.
