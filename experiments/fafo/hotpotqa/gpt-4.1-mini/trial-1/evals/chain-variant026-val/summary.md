# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 76.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.009 |
| summarize_hop1 | 3.382 | 3.123 | 5.829 |
| query_hop2 | 1.765 | 1.581 | 2.835 |
| retrieve_hop2 | 0.398 | 0.002 | 1.588 |
| summarize_hop2 | 3.135 | 2.894 | 4.972 |
| answer | 1.685 | 1.477 | 3.088 |
| **Total** | **10.390** | **9.780** | **15.081** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
