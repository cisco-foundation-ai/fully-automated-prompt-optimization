# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.03

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.035 |
| summarize_hop1 | 3.437 | 3.167 | 5.942 |
| query_hop2 | 1.856 | 1.653 | 3.314 |
| retrieve_hop2 | 0.952 | 0.209 | 1.731 |
| summarize_hop2 | 2.534 | 2.423 | 3.675 |
| answer | 1.195 | 1.095 | 1.958 |
| **Total** | **10.012** | **9.288** | **14.810** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
