# Evaluation Summary

Total cases: 150

## Composite Score
- average: 73.33

## Score Breakdown
- exact_match: 73.33
- f1: 78.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.128 | 0.002 | 0.071 |
| summarize_hop1 | 1.612 | 1.393 | 2.100 |
| query_hop2 | 1.119 | 0.996 | 1.502 |
| retrieve_hop2 | 0.719 | 0.003 | 1.697 |
| summarize_hop2 | 1.255 | 1.187 | 1.738 |
| answer | 0.898 | 0.849 | 1.194 |
| **Total** | **5.731** | **4.925** | **10.218** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
