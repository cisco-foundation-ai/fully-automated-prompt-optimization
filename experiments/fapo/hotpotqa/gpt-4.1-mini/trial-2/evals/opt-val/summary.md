# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 75.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.009 |
| summarize_hop1 | 3.137 | 2.905 | 5.143 |
| query_hop2 | 1.636 | 1.417 | 3.008 |
| retrieve_hop2 | 0.405 | 0.002 | 1.491 |
| summarize_hop2 | 3.138 | 2.808 | 5.112 |
| answer | 1.353 | 1.155 | 2.001 |
| **Total** | **9.704** | **9.121** | **13.952** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
