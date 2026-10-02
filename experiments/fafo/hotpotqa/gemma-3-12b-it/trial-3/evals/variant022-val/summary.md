# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.00

## Score Breakdown
- exact_match: 60.00
- f1: 68.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.010 |
| summarize_hop1 | 1.791 | 1.635 | 3.321 |
| query_hop2 | 0.982 | 0.944 | 1.364 |
| retrieve_hop2 | 0.569 | 0.004 | 1.597 |
| summarize_hop2 | 2.800 | 2.722 | 4.604 |
| answer | 1.133 | 1.053 | 1.968 |
| **Total** | **7.305** | **6.873** | **11.254** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 120 |
