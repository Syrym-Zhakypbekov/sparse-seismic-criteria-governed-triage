# PLAN undefined_snr (post hoc sensitivity variant; written and pushed before any computation)

Variant (not a change to the frozen rule): an episode whose reference SNR is undefined is ESCALATED by CG, CG-D and CG c = 0.5
instead of being scored on neighbour evidence alone. P3 and P1 are unchanged (P3 never dismisses or alerts without a valid SNR).
- Data: the 33 reviewed-label networks of Section 4.12 (frozen decisions, results/posthoc/_collect_reviewed.pkl).
- Report: number of episodes with undefined SNR; decisions that change (by from-action); reviewed-associated dismissals
  that change; pooled difference vs P3 with the two-stage cluster bootstrap (2000, seed 7), margin 3, ratio 1.5, for the frozen and
  the variant rules; whether any verdict changes.
- Output: results/review2/undefined_snr.json. Reported whatever the result.
