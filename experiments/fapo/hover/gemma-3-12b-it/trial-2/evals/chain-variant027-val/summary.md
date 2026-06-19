# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.67
- recall: 74.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.009 |
| summarize_hop1 | 3.286 | 2.724 | 6.830 |
| query_hop2 | 0.578 | 0.295 | 0.764 |
| retrieve_hop2 | 0.436 | 0.002 | 1.505 |
| summarize_hop2 | 6.272 | 5.954 | 10.036 |
| query_hop3 | 1.405 | 0.336 | 0.671 |
| retrieve_hop3 | 0.883 | 1.054 | 1.531 |
| summarize_hop3 | 7.344 | 5.952 | 12.618 |
| query_hop4 | 0.493 | 0.422 | 0.860 |
| retrieve_hop4 | 1.245 | 1.208 | 1.578 |
| query_hop5 | 0.418 | 0.368 | 0.662 |
| retrieve_hop5 | 1.253 | 1.284 | 1.578 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.617** | **21.075** | **30.783** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 77 |
