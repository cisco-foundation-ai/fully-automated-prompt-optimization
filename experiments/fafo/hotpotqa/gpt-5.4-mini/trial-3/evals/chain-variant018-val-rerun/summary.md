# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.33

## Score Breakdown
- exact_match: 73.33
- f1: 79.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.037 | 0.002 | 0.008 |
| summarize_hop1 | 1.353 | 1.159 | 1.882 |
| query_hop2 | 1.167 | 0.980 | 1.944 |
| retrieve_hop2 | 0.517 | 0.002 | 1.603 |
| summarize_hop2 | 1.331 | 1.148 | 1.763 |
| answer | 0.998 | 0.847 | 1.383 |
| **Total** | **5.403** | **4.595** | **8.698** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 79 |
| query_hop2 | 1 |
