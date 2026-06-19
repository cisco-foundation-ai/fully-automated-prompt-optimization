# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.67

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- num_missing: 0.39
- partial_recall: 87.00
- recall: 64.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.007 |
| summarize_hop1 | 2.552 | 2.113 | 5.183 |
| query_hop2 | 0.320 | 0.293 | 0.455 |
| retrieve_hop2 | 0.961 | 1.294 | 1.642 |
| summarize_hop2 | 5.811 | 5.431 | 9.965 |
| query_hop3 | 0.386 | 0.338 | 0.624 |
| retrieve_hop3 | 1.551 | 1.559 | 1.669 |
| summarize_hop3 | 13.487 | 11.661 | 18.088 |
| query_hop4 | 0.406 | 0.361 | 0.711 |
| retrieve_hop4 | 1.410 | 1.545 | 1.656 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **26.887** | **24.209** | **35.727** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 106 |
