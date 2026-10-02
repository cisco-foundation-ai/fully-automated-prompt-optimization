# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 70.60

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.037 | 0.002 | 0.013 |
| summarize_hop1 | 2.443 | 2.257 | 4.362 |
| query_hop2 | 1.050 | 1.002 | 1.612 |
| retrieve_hop2 | 0.517 | 0.002 | 1.627 |
| summarize_hop2 | 2.696 | 2.521 | 4.492 |
| answer | 1.072 | 0.998 | 1.570 |
| **Total** | **7.815** | **7.524** | **11.291** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
