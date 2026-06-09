# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 82.03

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.002 | 0.031 |
| summarize_hop1 | 1.412 | 1.304 | 2.125 |
| query_hop2 | 1.292 | 1.044 | 2.617 |
| retrieve_hop2 | 0.614 | 0.002 | 1.691 |
| summarize_hop2 | 1.526 | 1.285 | 2.455 |
| answer | 1.191 | 0.935 | 2.082 |
| **Total** | **6.067** | **5.040** | **11.463** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
