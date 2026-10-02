# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 77.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.067 | 0.002 | 0.094 |
| summarize_hop1 | 1.408 | 1.266 | 2.166 |
| query_hop2 | 1.144 | 1.025 | 1.715 |
| retrieve_hop2 | 0.611 | 0.002 | 1.659 |
| summarize_hop2 | 1.613 | 1.510 | 2.445 |
| answer | 0.835 | 0.746 | 1.230 |
| **Total** | **5.679** | **4.937** | **8.814** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
