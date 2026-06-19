# Evaluation Summary

Total cases: 300

## Composite Score
- average: 53.00

## Score Breakdown
- num_found: 2.44
- num_gold: 3.00
- num_missing: 0.56
- partial_recall: 81.44
- recall: 53.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.987 | 0.533 | 1.708 |
| summarize_hop1 | 2.545 | 2.221 | 4.433 |
| query_hop2 | 0.784 | 0.680 | 1.050 |
| retrieve_hop2 | 1.358 | 1.332 | 1.645 |
| summarize_hop2 | 2.910 | 2.641 | 5.022 |
| query_hop3 | 0.847 | 0.696 | 1.099 |
| retrieve_hop3 | 1.343 | 1.325 | 1.650 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.775** | **10.197** | **14.937** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 141 |
