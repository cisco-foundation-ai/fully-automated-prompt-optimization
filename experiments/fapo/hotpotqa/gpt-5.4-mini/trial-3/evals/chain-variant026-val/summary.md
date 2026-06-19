# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.05

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.009 |
| summarize_hop1 | 1.311 | 1.264 | 1.800 |
| query_hop2 | 1.067 | 1.040 | 1.387 |
| retrieve_hop2 | 0.403 | 0.002 | 1.623 |
| summarize_hop2 | 1.326 | 1.261 | 1.764 |
| answer | 1.022 | 0.897 | 1.330 |
| **Total** | **5.169** | **4.726** | **6.975** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 82 |
