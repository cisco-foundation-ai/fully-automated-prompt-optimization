# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.30

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.060 | 0.002 | 0.053 |
| summarize_hop1 | 1.968 | 1.809 | 3.261 |
| query_hop2 | 1.050 | 1.018 | 1.320 |
| retrieve_hop2 | 0.623 | 0.003 | 1.665 |
| summarize_hop2 | 3.128 | 2.997 | 4.801 |
| answer | 1.399 | 1.302 | 2.063 |
| **Total** | **8.227** | **7.772** | **12.640** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
