# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.00

## Score Breakdown
- exact_match: 76.00
- f1: 82.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.021 |
| summarize_hop1 | 1.531 | 1.347 | 2.174 |
| query_hop2 | 1.165 | 0.956 | 1.818 |
| retrieve_hop2 | 0.685 | 0.002 | 1.651 |
| summarize_hop2 | 1.269 | 1.206 | 1.730 |
| answer | 0.985 | 0.910 | 1.365 |
| **Total** | **5.674** | **4.792** | **8.584** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 36 |
