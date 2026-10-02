# Evaluation Summary

Total cases: 300

## Composite Score
- average: 55.00

## Score Breakdown
- exact_match: 55.00
- f1: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 2.853 | 1.416 | 4.502 |
| query_hop2 | 2.527 | 1.239 | 3.127 |
| retrieve_hop2 | 1.496 | 1.499 | 1.665 |
| summarize_hop2 | 2.456 | 1.329 | 3.700 |
| answer | 1.609 | 1.201 | 3.263 |
| **Total** | **10.945** | **7.112** | **15.129** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 135 |
