# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.056 | 0.002 | 0.035 |
| summarize_hop1 | 2.346 | 2.252 | 3.871 |
| query_hop2 | 1.014 | 0.966 | 1.393 |
| retrieve_hop2 | 0.877 | 1.051 | 1.650 |
| summarize_hop2 | 2.514 | 2.429 | 3.744 |
| answer | 1.008 | 0.968 | 1.433 |
| **Total** | **7.815** | **7.554** | **10.469** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
