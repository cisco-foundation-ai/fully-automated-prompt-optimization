# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 73.62

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.024 |
| summarize_hop1 | 2.268 | 2.166 | 3.752 |
| query_hop2 | 0.965 | 0.929 | 1.362 |
| retrieve_hop2 | 1.631 | 1.540 | 1.699 |
| summarize_hop2 | 2.649 | 2.500 | 4.651 |
| answer | 1.071 | 1.036 | 1.663 |
| **Total** | **8.616** | **8.117** | **12.731** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
