# Deviations from PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md (dffacba)
- 2026-11-08 ~05:40Z: the secondary label REVIEWED-OR-ACCEPTED (§4) was not computed by the pushed scorer. Every ISC catalogue row
  of every network matched an event in the ISC service (rows_matched = catalogue_rows for all 38 networks), so that label equals the
  ISC rows of the original catalogue association plus reviewed USGS rows; it is not reported separately.
- Epicentral tolerance implemented as |dlat| <= 0.5 deg and |dlon| <= 0.5 deg / cos(lat); the plan says "epicentral difference
  <= 0.5 deg". Every row was matched within 2 s, so the tolerance did not change any label.
- The OSF copy of this plan was filled in after the GitHub push and before scoring; it was submitted by the authors later (if at all),
  so the GitHub push (2026-11-08T04:40:20Z) remains the timestamp of record.
