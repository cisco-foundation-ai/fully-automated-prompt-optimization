# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- exact_match: 72.33
- f1: 78.34

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.051 | 0.002 | 0.008 |
| summarize_hop1 | 1.359 | 1.288 | 2.080 |
| query_hop2 | 1.064 | 1.002 | 1.454 |
| retrieve_hop2 | 0.394 | 0.002 | 1.581 |
| summarize_hop2 | 1.325 | 1.268 | 1.887 |
| answer | 0.945 | 0.889 | 1.314 |
| **Total** | **5.139** | **4.759** | **6.730** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 83 |
