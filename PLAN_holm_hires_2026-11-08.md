# PLAN holm_hires (post hoc; written and pushed before any computation)

High-resolution bootstrap so that Holm over the enlarged family is resolvable (2000 resamples give p >= 1/2001).
- Pooled contrasts, two-stage cluster bootstrap with 20,000 resamples, seed 7: CG, CG-D, CG c = 0.5 minus P3 on the 33 reviewed
  networks (one-sided p of H0: difference >= 3 points); context T1 H1 (CG-ctx minus P3, H0 >= 3 points) and H2 (CG-ctx minus
  CG c = 0.5, H0 >= 0).
- Per-network day bootstraps (published analysis/v2_networks.day_boot) with 20,000 resamples for CG, CG-D, CG c = 0.5 minus P3 on the
  33 networks.
- The 9 earlier tests of results/posthoc/cold_panel_posthoc.json are added with their published p values (their resolution is stated).
- Holm and Benjamini-Yekutieli at one-sided alpha 0.025 over the whole family; reported: family size, met unadjusted, met after
  Holm, met after BY, and the adjusted p of each pooled contrast.
- Output: results/review2/holm_hires.json. Reported whatever the result.
