# Evaluation Summary

Total cases: 300

## Composite Score
- average: 98.67

## Score Breakdown
- num_found: 2.99
- num_gold: 3.00
- partial_recall: 99.56
- recall: 98.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.983 | 0.537 | 1.651 |
| summarize_hop1 | 37.838 | 28.642 | 78.455 |
| query_hop2 | 1.720 | 1.332 | 4.301 |
| retrieve_hop2 | 10.291 | 10.880 | 12.319 |
| summarize_hop2 | 47.028 | 28.086 | 141.338 |
| query_hop3 | 1.853 | 1.299 | 5.548 |
| retrieve_hop3 | 8.644 | 8.804 | 11.737 |
| summarize_hop3 | 39.099 | 27.537 | 130.932 |
| query_hop4 | 1.900 | 1.589 | 4.069 |
| retrieve_hop4 | 9.705 | 9.848 | 14.279 |
| summarize_hop4 | 42.978 | 35.861 | 78.647 |
| query_hop5 | 3.108 | 2.333 | 7.438 |
| retrieve_hop5 | 16.491 | 16.082 | 23.260 |
| combine_retrievals | 0.011 | 0.010 | 0.020 |
| **Total** | **221.649** | **187.875** | **439.999** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 4 |
