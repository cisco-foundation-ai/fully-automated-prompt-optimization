# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.28

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.150 | 0.002 | 0.107 |
| summarize_hop1 | 1.420 | 1.302 | 2.114 |
| query_hop2 | 1.105 | 1.036 | 1.606 |
| retrieve_hop2 | 0.484 | 0.002 | 1.640 |
| summarize_hop2 | 1.542 | 1.494 | 2.266 |
| answer | 0.814 | 0.766 | 1.314 |
| **Total** | **5.516** | **5.008** | **7.819** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
