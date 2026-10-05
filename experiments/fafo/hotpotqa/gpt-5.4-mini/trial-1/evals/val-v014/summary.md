# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.16

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.048 | 0.002 | 0.100 |
| summarize_hop1 | 1.370 | 1.288 | 2.030 |
| query_hop2 | 1.117 | 1.041 | 1.599 |
| retrieve_hop2 | 1.042 | 0.100 | 1.694 |
| summarize_hop2 | 1.609 | 1.529 | 2.395 |
| answer | 0.813 | 0.754 | 1.141 |
| **Total** | **5.999** | **5.502** | **8.043** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
