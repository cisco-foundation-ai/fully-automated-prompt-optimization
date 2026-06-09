# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- num_missing: 0.38
- partial_recall: 87.33
- recall: 65.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 4.474 | 2.989 | 7.133 |
| query_hop2 | 0.326 | 0.298 | 0.508 |
| retrieve_hop2 | 0.591 | 0.002 | 1.618 |
| summarize_hop2 | 9.063 | 7.868 | 13.722 |
| query_hop3 | 0.399 | 0.346 | 0.659 |
| retrieve_hop3 | 1.338 | 1.530 | 1.659 |
| summarize_hop3 | 12.447 | 11.199 | 19.371 |
| query_hop4 | 0.429 | 0.363 | 0.830 |
| retrieve_hop4 | 1.285 | 1.536 | 1.657 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **30.356** | **26.508** | **42.070** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 104 |
