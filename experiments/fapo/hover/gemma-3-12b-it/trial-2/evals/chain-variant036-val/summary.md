# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.67

## Score Breakdown
- num_found: 2.75
- num_gold: 3.00
- num_missing: 0.25
- partial_recall: 91.78
- recall: 78.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.430 | 3.066 | 6.478 |
| query_hop2 | 0.405 | 0.331 | 0.848 |
| retrieve_hop2 | 1.266 | 1.423 | 1.661 |
| summarize_hop2 | 7.203 | 6.120 | 11.491 |
| query_hop3 | 0.419 | 0.334 | 1.096 |
| retrieve_hop3 | 1.122 | 1.406 | 1.643 |
| summarize_hop3 | 8.986 | 7.274 | 13.497 |
| query_hop4 | 0.498 | 0.440 | 0.815 |
| retrieve_hop4 | 1.392 | 1.492 | 1.685 |
| query_hop5 | 0.604 | 0.486 | 1.589 |
| retrieve_hop5 | 2.411 | 2.623 | 3.249 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **27.741** | **25.126** | **35.707** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 64 |
