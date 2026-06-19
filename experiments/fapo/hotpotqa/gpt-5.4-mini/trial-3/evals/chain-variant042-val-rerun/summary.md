# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.65

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.043 | 0.002 | 0.011 |
| summarize_hop1 | 1.421 | 1.268 | 2.083 |
| query_hop2 | 1.157 | 1.030 | 1.654 |
| retrieve_hop2 | 0.401 | 0.002 | 1.583 |
| summarize_hop2 | 1.403 | 1.272 | 2.103 |
| answer | 1.001 | 0.915 | 1.437 |
| **Total** | **5.427** | **4.842** | **8.373** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
| query_hop2 | 1 |
