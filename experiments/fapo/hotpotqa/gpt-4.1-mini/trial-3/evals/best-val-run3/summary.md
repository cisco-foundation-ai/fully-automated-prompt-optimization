# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 77.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.009 |
| summarize_hop1 | 5.326 | 4.822 | 10.465 |
| query_hop2 | 2.415 | 2.191 | 3.959 |
| retrieve_hop2 | 0.562 | 0.004 | 1.567 |
| summarize_hop2 | 4.304 | 3.875 | 7.420 |
| answer | 2.049 | 1.683 | 3.875 |
| **Total** | **14.681** | **14.069** | **22.194** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 89 |
