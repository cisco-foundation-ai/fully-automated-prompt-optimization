# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 73.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.009 |
| summarize_hop1 | 1.881 | 1.782 | 2.620 |
| query_hop2 | 1.120 | 1.047 | 1.599 |
| retrieve_hop2 | 0.517 | 0.002 | 1.612 |
| summarize_hop2 | 1.735 | 1.671 | 2.394 |
| answer | 0.869 | 0.798 | 1.455 |
| **Total** | **6.161** | **5.807** | **8.206** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
