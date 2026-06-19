# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.278 | 0.978 | 1.714 |
| summarize_hop1 | 1.405 | 1.309 | 2.153 |
| query_hop2 | 1.114 | 1.083 | 1.504 |
| retrieve_hop2 | 1.319 | 1.324 | 1.616 |
| summarize_hop2 | 1.740 | 1.622 | 2.399 |
| answer | 0.851 | 0.744 | 1.269 |
| **Total** | **7.705** | **7.226** | **10.294** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
