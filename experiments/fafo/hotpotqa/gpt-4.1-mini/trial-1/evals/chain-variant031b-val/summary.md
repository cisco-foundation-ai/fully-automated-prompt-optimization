# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.009 |
| summarize_hop1 | 4.374 | 4.030 | 7.205 |
| query_hop2 | 2.078 | 1.819 | 4.152 |
| retrieve_hop2 | 0.468 | 0.002 | 1.592 |
| summarize_hop2 | 3.212 | 2.809 | 5.313 |
| answer | 2.022 | 1.747 | 3.073 |
| **Total** | **12.172** | **11.479** | **18.508** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
