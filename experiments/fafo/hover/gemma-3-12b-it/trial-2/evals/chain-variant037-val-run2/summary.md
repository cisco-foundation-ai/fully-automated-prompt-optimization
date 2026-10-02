# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.67

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.44
- recall: 79.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.011 |
| summarize_hop1 | 3.316 | 2.827 | 6.374 |
| query_hop2 | 0.389 | 0.332 | 0.755 |
| retrieve_hop2 | 1.041 | 1.276 | 1.639 |
| summarize_hop2 | 6.595 | 6.281 | 10.038 |
| query_hop3 | 0.476 | 0.387 | 0.926 |
| retrieve_hop3 | 2.398 | 2.592 | 3.217 |
| summarize_hop3 | 7.037 | 6.760 | 12.376 |
| query_hop4 | 0.553 | 0.428 | 1.331 |
| retrieve_hop4 | 1.319 | 1.341 | 1.664 |
| query_hop5 | 0.587 | 0.481 | 1.056 |
| retrieve_hop5 | 2.193 | 2.185 | 3.201 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.908** | **25.614** | **35.080** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 61 |
