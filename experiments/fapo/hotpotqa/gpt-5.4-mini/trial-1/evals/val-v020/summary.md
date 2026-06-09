# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 75.38

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.125 | 0.002 | 0.129 |
| summarize_hop1 | 1.318 | 1.236 | 2.001 |
| query_hop2 | 1.102 | 1.020 | 1.541 |
| retrieve_hop2 | 0.445 | 0.002 | 1.636 |
| summarize_hop2 | 1.729 | 1.448 | 2.348 |
| answer | 0.829 | 0.780 | 1.358 |
| **Total** | **5.548** | **4.835** | **7.479** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
