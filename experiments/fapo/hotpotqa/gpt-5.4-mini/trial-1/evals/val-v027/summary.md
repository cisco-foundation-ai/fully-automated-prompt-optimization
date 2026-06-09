# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 74.34

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.128 | 0.002 | 0.116 |
| summarize_hop1 | 1.237 | 1.143 | 1.831 |
| query_hop2 | 1.152 | 1.054 | 1.908 |
| retrieve_hop2 | 0.405 | 0.002 | 1.591 |
| summarize_hop2 | 1.540 | 1.478 | 2.281 |
| answer | 0.833 | 0.795 | 1.206 |
| **Total** | **5.294** | **4.739** | **7.516** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
