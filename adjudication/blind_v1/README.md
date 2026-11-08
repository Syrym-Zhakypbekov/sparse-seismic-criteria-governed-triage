# Blind waveform adjudication, package v1 (planned; not yet adjudicated)

For a seismic analyst. 102 cases, neutral ids C001-C102. Each plot shows the reference station (top) and its neighbour
stations, vertical component, 1-8 Hz band-pass, 180 s window starting 60 s before the alarm onset. No rule decision,
catalogue label or case class is shown, and the case order is random.

Task: for each case fill ANALYST_FORM.csv: is there a seismic signal on the reference trace (yes/no/unsure), and on any
neighbour (yes/no/unsure); free notes. Stream names and UTC windows are in cases.csv if you want to inspect the raw data.

The key (class, network, time, rule actions) is kept outside this repository and is opened only after the form is complete.
Built by analysis/blind_adjudication_package.py (plan: PLAN_TWOTHRESHOLD_2026-11-08.md, addendum item 5; seed 7).
