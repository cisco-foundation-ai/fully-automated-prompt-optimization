# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.063 | 0.002 | 0.010 |
| summarize_hop1 | 1.377 | 1.281 | 1.984 |
| query_hop2 | 1.145 | 1.039 | 1.832 |
| retrieve_hop2 | 0.257 | 0.002 | 1.567 |
| summarize_hop2 | 1.424 | 1.300 | 2.139 |
| answer | 1.032 | 0.940 | 1.596 |
| **Total** | **5.298** | **4.888** | **8.104** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
