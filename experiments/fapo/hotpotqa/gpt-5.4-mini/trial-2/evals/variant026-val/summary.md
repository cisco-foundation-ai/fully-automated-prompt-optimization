# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 74.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.009 |
| summarize_hop1 | 2.342 | 2.206 | 3.561 |
| query_hop2 | 1.180 | 1.116 | 1.647 |
| retrieve_hop2 | 0.392 | 0.002 | 1.609 |
| summarize_hop2 | 1.852 | 1.764 | 2.553 |
| answer | 0.830 | 0.752 | 1.298 |
| **Total** | **6.636** | **6.349** | **9.097** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
