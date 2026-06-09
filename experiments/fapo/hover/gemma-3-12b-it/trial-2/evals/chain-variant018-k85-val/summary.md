# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- num_missing: 0.33
- partial_recall: 89.11
- recall: 69.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.009 | 0.575 | 1.739 |
| summarize_hop1 | 4.300 | 3.038 | 7.918 |
| query_hop2 | 0.366 | 0.332 | 0.532 |
| retrieve_hop2 | 1.386 | 1.395 | 1.692 |
| summarize_hop2 | 8.667 | 8.225 | 13.711 |
| query_hop3 | 0.373 | 0.344 | 0.623 |
| retrieve_hop3 | 1.268 | 1.355 | 1.681 |
| summarize_hop3 | 8.561 | 7.289 | 14.193 |
| query_hop4 | 0.491 | 0.450 | 0.837 |
| retrieve_hop4 | 1.357 | 1.386 | 1.702 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **27.779** | **25.542** | **38.144** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 91 |
