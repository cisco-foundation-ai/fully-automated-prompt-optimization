# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.25

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.128 | 0.002 | 0.126 |
| summarize_hop1 | 1.291 | 1.208 | 1.975 |
| query_hop2 | 1.048 | 1.009 | 1.425 |
| retrieve_hop2 | 0.487 | 0.002 | 1.551 |
| summarize_hop2 | 1.524 | 1.417 | 2.171 |
| answer | 0.903 | 0.776 | 1.168 |
| **Total** | **5.381** | **4.713** | **7.837** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
