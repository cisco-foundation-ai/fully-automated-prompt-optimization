# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.061 | 0.002 | 0.011 |
| summarize_hop1 | 1.363 | 1.264 | 1.975 |
| query_hop2 | 1.034 | 0.988 | 1.371 |
| retrieve_hop2 | 0.343 | 0.002 | 1.509 |
| summarize_hop2 | 1.309 | 1.231 | 1.877 |
| answer | 0.939 | 0.876 | 1.364 |
| **Total** | **5.048** | **4.679** | **6.989** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 82 |
