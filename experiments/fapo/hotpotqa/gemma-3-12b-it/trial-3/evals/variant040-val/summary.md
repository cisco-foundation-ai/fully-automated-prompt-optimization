# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.33

## Score Breakdown
- exact_match: 60.33
- f1: 69.23

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.012 |
| summarize_hop1 | 2.322 | 2.242 | 3.662 |
| query_hop2 | 1.056 | 1.018 | 1.534 |
| retrieve_hop2 | 0.459 | 0.002 | 1.563 |
| summarize_hop2 | 3.391 | 3.266 | 5.427 |
| answer | 1.150 | 1.073 | 1.763 |
| **Total** | **8.411** | **8.145** | **12.208** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
| summarize_hop2 | 1 |
