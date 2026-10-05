# Evaluation Summary

Total cases: 300

## Composite Score
- average: 27.67

## Score Breakdown
- num_found: 1.96
- num_gold: 3.00
- partial_recall: 65.22
- recall: 27.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.004 |
| summarize_hop1 | 3.831 | 3.280 | 7.227 |
| query_hop2 | 0.946 | 0.579 | 1.299 |
| retrieve_hop2 | 0.415 | 0.002 | 1.620 |
| summarize_hop2 | 5.071 | 3.765 | 11.426 |
| query_hop3 | 0.717 | 0.569 | 1.318 |
| retrieve_hop3 | 0.615 | 0.002 | 1.639 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.607** | **9.709** | **21.503** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 217 |
