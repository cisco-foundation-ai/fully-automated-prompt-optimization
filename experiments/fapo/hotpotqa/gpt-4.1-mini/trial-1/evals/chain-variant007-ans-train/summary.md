# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.053 |
| summarize_hop1 | 4.761 | 4.107 | 8.229 |
| query_hop2 | 1.726 | 1.631 | 2.483 |
| retrieve_hop2 | 0.617 | 0.089 | 1.658 |
| summarize_hop2 | 2.923 | 2.466 | 5.066 |
| answer | 2.291 | 1.952 | 4.198 |
| **Total** | **12.358** | **11.644** | **19.508** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
