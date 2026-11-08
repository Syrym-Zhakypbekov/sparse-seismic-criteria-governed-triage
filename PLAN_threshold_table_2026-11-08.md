# PLAN threshold_table (verification; written and pushed before any computation)

Table A2 (analysis/threshold_table.py, numeric scan of v2_networks.policies) is checked independently.
- c = 1 and c = 0.5: closed-form thresholds from the frozen formula: with Y = sum of YES weights, Q = Y + c x sum of NO weights,
  den = Q + 0.40 (valid SNR); dismiss iff den >= 0.45 and (Y + 0.40 min(SNR/30, 1)) / den <= 0.16; alert iff >= 0.60.
- CG-D: per-bin closed form with the development-table weights of each SNR bin.
- Comparison: every cell of Table A2 vs the closed form (tolerance 0.01 dB, the grid step).
- Episode check: on the 33 reviewed networks, the action predicted from the closed-form thresholds for every episode with a valid
  SNR vs the frozen action; mismatches counted per policy.
- Output: results/review2/threshold_table.json. Mismatches reported.
