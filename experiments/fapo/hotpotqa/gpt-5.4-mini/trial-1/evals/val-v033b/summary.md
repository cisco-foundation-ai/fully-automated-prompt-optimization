# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 75.19

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.131 | 0.002 | 0.113 |
| summarize_hop1 | 1.354 | 1.277 | 2.061 |
| query_hop2 | 1.139 | 1.051 | 1.816 |
| retrieve_hop2 | 0.362 | 0.002 | 1.605 |
| summarize_hop2 | 1.591 | 1.514 | 2.258 |
| answer | 0.773 | 0.752 | 1.113 |
| **Total** | **5.350** | **4.771** | **7.566** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
| query_hop2 | 2 |
