# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 75.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.009 |
| summarize_hop1 | 3.330 | 3.074 | 5.853 |
| query_hop2 | 1.942 | 1.664 | 3.415 |
| retrieve_hop2 | 0.432 | 0.004 | 1.321 |
| summarize_hop2 | 3.101 | 2.893 | 5.107 |
| answer | 1.856 | 1.530 | 3.582 |
| **Total** | **10.676** | **9.985** | **16.172** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
