# Evaluation Summary

Total cases: 150

## Composite Score
- average: 73.33

## Score Breakdown
- exact_match: 73.33
- f1: 77.72

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.039 |
| summarize_hop1 | 3.253 | 3.051 | 5.262 |
| query_hop2 | 1.137 | 1.087 | 1.588 |
| retrieve_hop2 | 0.483 | 0.002 | 1.587 |
| summarize_hop2 | 3.042 | 2.945 | 4.612 |
| answer | 0.960 | 0.881 | 1.523 |
| **Total** | **8.915** | **8.597** | **12.157** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
