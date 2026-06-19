# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 73.80

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 2.935 | 2.614 | 5.010 |
| query_hop2 | 1.615 | 1.502 | 2.600 |
| retrieve_hop2 | 0.736 | 0.290 | 1.674 |
| summarize_hop2 | 2.580 | 2.328 | 4.877 |
| answer | 1.132 | 1.055 | 1.782 |
| **Total** | **9.001** | **8.482** | **13.453** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
