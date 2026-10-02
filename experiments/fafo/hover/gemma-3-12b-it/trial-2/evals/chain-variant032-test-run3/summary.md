# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- num_missing: 0.30
- partial_recall: 90.11
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.534 | 2.681 | 8.792 |
| query_hop2 | 0.406 | 0.318 | 0.978 |
| retrieve_hop2 | 0.662 | 0.005 | 1.613 |
| summarize_hop2 | 6.178 | 5.955 | 9.980 |
| query_hop3 | 0.402 | 0.333 | 0.833 |
| retrieve_hop3 | 0.961 | 1.260 | 1.654 |
| summarize_hop3 | 7.985 | 6.771 | 13.743 |
| query_hop4 | 0.550 | 0.419 | 1.346 |
| retrieve_hop4 | 1.362 | 1.524 | 1.674 |
| query_hop5 | 0.629 | 0.469 | 1.642 |
| retrieve_hop5 | 2.581 | 2.649 | 3.274 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.253** | **23.637** | **35.921** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 76 |
