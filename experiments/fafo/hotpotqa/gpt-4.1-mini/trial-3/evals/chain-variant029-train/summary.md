# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 80.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.038 |
| summarize_hop1 | 6.497 | 5.412 | 12.971 |
| query_hop2 | 2.425 | 2.083 | 4.776 |
| retrieve_hop2 | 0.674 | 0.093 | 1.610 |
| summarize_hop2 | 5.253 | 4.829 | 8.406 |
| answer | 2.704 | 2.375 | 4.999 |
| **Total** | **17.580** | **16.132** | **29.316** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
