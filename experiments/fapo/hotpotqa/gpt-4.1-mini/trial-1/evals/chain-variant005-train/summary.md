# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 78.43

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.002 | 0.017 |
| summarize_hop1 | 3.929 | 3.200 | 8.172 |
| query_hop2 | 1.912 | 1.752 | 3.425 |
| retrieve_hop2 | 0.677 | 0.095 | 1.713 |
| summarize_hop2 | 3.070 | 2.913 | 4.464 |
| answer | 1.420 | 1.312 | 2.104 |
| **Total** | **11.040** | **10.335** | **18.843** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
