# PLAN margin_cost (post hoc, descriptive; written and pushed before any computation)

Operational reading of the 3-point margin from the 33-network workload counts (results/posthoc/twothreshold.json analyst_items).
- Cost of a policy = 2 min x escalations + f x unassociated automatic alerts + k x dismissed reviewed-associated alarms, with
  f in {0, 0.5, 1, 2} analyst-minutes per false automatic alert and k in {30, 60, 120, 240} analyst-minutes per dismissed
  reviewed-associated alarm.
- Break-even margin of a policy X vs P3 = the extra dismissed share (points of reviewed-associated alarms) at which
  cost(X) = cost(P3): [2 (E_P3 - E_X) + f (UA_P3 - UA_X)] / k / N_assoc x 100.
- Reported for CG c = 0.5 and CG-D: the break-even margin, whether the observed difference (0.74 / 0.97) and the 3-point margin are
  below it (cost-neutral or better) or above it, i.e. whether 3 points is lenient or strict under each (f, k).
- Output: results/review2/margin_cost.json.
