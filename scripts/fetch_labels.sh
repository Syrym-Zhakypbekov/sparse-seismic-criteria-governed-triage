#!/usr/bin/env bash
# Re-download the bulletin label files that are not redistributed in this repository (about 140 MB).
# Each scorer has a "download" step that queries the ISC and USGS FDSN event services and records the SHA-256 of what it
# received. Compare the new hashes with results/*/labels/SHA256.txt and results/*/labels/download_record.json.
# Run from the repository root.
set -euo pipefail
PY=${PY:-python}

$PY analysis/v2_reviewed_bulletin.py download     # Table 18: ISC Reviewed Bulletin and ComCat reviewed events, 33 networks
$PY analysis/v2_reviewed_ext12B.py download       # Table 15 secondary scoring: reviewed labels of the 12-month extension
$PY analysis/v2_rescue_score.py download          # Table 16: rescued networks
$PY analysis/ground_truth_v2.py download          # Table 17: ComCat analyst-confirmed and analyst-deleted events, Alaska
$PY analysis/kz_reviewed_labels.py download       # Table 20: ISC-reviewed events, Kazakhstan
$PY analysis/explosions_v2.py download            # Section 4.13: ComCat event types
$PY analysis/nnc_provenance.py                    # Appendix C: monthly NNC queries (raw QuakeML in results/nnc/raw/)
