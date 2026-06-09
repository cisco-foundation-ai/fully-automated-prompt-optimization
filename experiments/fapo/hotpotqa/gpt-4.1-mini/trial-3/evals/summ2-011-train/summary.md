# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 81.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.007 |
| summarize_hop1 | 4.752 | 4.147 | 8.221 |
| query_hop2 | 3.354 | 2.952 | 6.937 |
| retrieve_hop2 | 1.061 | 1.066 | 1.637 |
| summarize_hop2 | 5.025 | 4.470 | 8.674 |
| answer | 2.143 | 1.800 | 4.455 |
| **Total** | **16.362** | **15.304** | **25.916** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
