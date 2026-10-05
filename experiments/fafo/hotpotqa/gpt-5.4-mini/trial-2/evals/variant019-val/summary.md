# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 77.07

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.036 | 0.002 | 0.009 |
| summarize_hop1 | 2.291 | 2.245 | 3.324 |
| query_hop2 | 1.173 | 1.103 | 1.591 |
| retrieve_hop2 | 0.384 | 0.002 | 1.580 |
| summarize_hop2 | 1.820 | 1.735 | 2.627 |
| answer | 1.187 | 1.128 | 1.547 |
| **Total** | **6.891** | **6.671** | **9.089** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
