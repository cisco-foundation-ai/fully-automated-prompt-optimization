# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 75.53

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.006 |
| summarize_hop1 | 1.722 | 1.550 | 2.294 |
| query_hop2 | 1.375 | 1.131 | 2.361 |
| retrieve_hop2 | 0.369 | 0.002 | 1.551 |
| summarize_hop2 | 1.664 | 1.507 | 2.435 |
| answer | 1.018 | 0.817 | 1.449 |
| **Total** | **6.182** | **5.396** | **10.421** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
