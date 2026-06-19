# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.002 | 0.008 |
| summarize_hop1 | 1.468 | 1.375 | 2.035 |
| query_hop2 | 1.062 | 0.940 | 1.549 |
| retrieve_hop2 | 0.403 | 0.002 | 1.619 |
| summarize_hop2 | 1.288 | 1.140 | 1.798 |
| answer | 0.915 | 0.845 | 1.492 |
| **Total** | **5.166** | **4.631** | **7.273** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
