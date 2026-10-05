# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 77.63

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.985 | 0.570 | 1.600 |
| summarize_hop1 | 4.690 | 4.303 | 8.160 |
| query_hop2 | 2.749 | 2.550 | 4.475 |
| retrieve_hop2 | 1.275 | 1.282 | 1.584 |
| summarize_hop2 | 4.794 | 4.290 | 8.208 |
| answer | 1.843 | 1.610 | 3.407 |
| **Total** | **16.337** | **15.496** | **23.668** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
