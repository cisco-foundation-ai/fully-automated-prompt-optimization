# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.53

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.011 |
| summarize_hop1 | 4.266 | 3.758 | 8.080 |
| query_hop2 | 2.242 | 1.966 | 4.089 |
| retrieve_hop2 | 0.284 | 0.002 | 1.536 |
| summarize_hop2 | 2.946 | 2.729 | 4.748 |
| answer | 2.024 | 1.832 | 3.333 |
| **Total** | **11.778** | **11.081** | **18.309** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
