# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 74.80

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.008 |
| summarize_hop1 | 3.243 | 2.872 | 6.079 |
| query_hop2 | 1.839 | 1.669 | 3.042 |
| retrieve_hop2 | 0.615 | 0.002 | 1.627 |
| summarize_hop2 | 3.097 | 2.887 | 5.027 |
| answer | 1.776 | 1.573 | 3.193 |
| **Total** | **10.603** | **10.044** | **15.248** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
