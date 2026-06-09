# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 74.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.010 |
| summarize_hop1 | 2.251 | 2.162 | 3.344 |
| query_hop2 | 1.164 | 1.099 | 1.582 |
| retrieve_hop2 | 0.516 | 0.002 | 1.566 |
| summarize_hop2 | 1.814 | 1.719 | 2.705 |
| answer | 0.885 | 0.827 | 1.383 |
| **Total** | **6.653** | **6.332** | **8.728** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
