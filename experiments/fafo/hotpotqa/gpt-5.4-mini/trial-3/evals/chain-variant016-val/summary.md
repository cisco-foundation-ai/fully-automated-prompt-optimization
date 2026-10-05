# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.007 |
| summarize_hop1 | 1.432 | 1.365 | 1.955 |
| query_hop2 | 1.013 | 0.907 | 1.497 |
| retrieve_hop2 | 0.549 | 0.002 | 1.625 |
| summarize_hop2 | 1.229 | 1.159 | 1.598 |
| answer | 0.874 | 0.843 | 1.158 |
| **Total** | **5.127** | **4.598** | **6.829** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 84 |
