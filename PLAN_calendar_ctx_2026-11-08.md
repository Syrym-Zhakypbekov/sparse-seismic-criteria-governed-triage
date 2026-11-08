# PLAN calendar_ctx (post hoc; written and pushed before any computation)

Shared-calendar bootstrap for the context-dependent reliability test T1 (Section 4.15; 26 batch-B networks, reviewed labels).
- Statistics: H1 = CG-ctx minus P3, H2 = CG-ctx minus CG c = 0.5, pooled difference of dismissed reviewed-associated shares (points)
  and ratio (D + 0.5)/(D_ref + 0.5).
- Resampling as analysis/calendar_bootstrap.py: networks with replacement and ONE common sequence of circular calendar-day blocks
  (block length 1, 7, 14, 28 days) applied to every drawn network; 10,000 replicates, seed 7.
- Criteria as pre-specified for H1 (upper 95% bound <= 3 points; ratio <= 1.5) and H2 (upper bound of the difference < 0).
- Output: results/review2/calendar_ctx.json. Reported whatever the result.
