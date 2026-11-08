# Run note — evidence-sufficiency stress test (plan e30842d)

- Full run: laptop, 8 worker processes, 50 masking seeds (7..56) x 500 bootstrap draws, 204.6 s, 08.11.2026 ~15:50 Almaty.
  Log: `laptop.log`. Reproduction check of the unmasked archive: 0 mismatches for P1, P3, CG, CG c=0.5, CG-D.
- Deviation from the plan: the plan named VM p10-seismic as the compute host. SSH to the VM failed after a laptop restart
  (gcloud re-authentication pending), so the identical script ran on the laptop. The host does not affect the numbers
  (fixed seeds, same input file `results/posthoc/_collect_reviewed.pkl`).
- `stress_smoke_seed7_only.json` is the first pass with one masking seed (13 s), kept for the record; the reported
  result is `stress.json` (50 seeds).
- Figure `figures/fig7_sufficiency.png` named in the plan is not produced by this script; to be drawn from `stress.json`.
