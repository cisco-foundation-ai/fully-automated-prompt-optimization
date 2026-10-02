# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.151 | 0.002 | 0.115 |
| summarize_hop1 | 1.325 | 1.229 | 1.955 |
| query_hop2 | 1.126 | 1.046 | 1.697 |
| retrieve_hop2 | 0.432 | 0.002 | 1.637 |
| summarize_hop2 | 1.516 | 1.449 | 2.240 |
| answer | 0.803 | 0.743 | 1.183 |
| **Total** | **5.352** | **4.726** | **8.075** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
