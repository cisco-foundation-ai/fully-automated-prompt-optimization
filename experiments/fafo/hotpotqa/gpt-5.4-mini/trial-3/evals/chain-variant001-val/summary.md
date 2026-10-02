# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.00

## Score Breakdown
- exact_match: 62.00
- f1: 70.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.010 |
| summarize_hop1 | 1.179 | 1.099 | 1.744 |
| query_hop2 | 1.002 | 0.938 | 1.447 |
| retrieve_hop2 | 0.577 | 0.002 | 1.691 |
| summarize_hop2 | 1.124 | 1.050 | 1.568 |
| answer | 1.016 | 0.956 | 1.545 |
| **Total** | **4.937** | **4.483** | **7.068** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 114 |
