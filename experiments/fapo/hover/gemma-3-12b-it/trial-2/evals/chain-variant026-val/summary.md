# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.67

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.67
- recall: 75.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.336 | 2.809 | 6.892 |
| query_hop2 | 0.376 | 0.316 | 0.731 |
| retrieve_hop2 | 0.388 | 0.002 | 1.498 |
| summarize_hop2 | 6.373 | 5.989 | 10.446 |
| query_hop3 | 0.403 | 0.328 | 0.825 |
| retrieve_hop3 | 0.796 | 1.064 | 1.557 |
| summarize_hop3 | 7.966 | 6.512 | 12.399 |
| query_hop4 | 0.484 | 0.427 | 0.794 |
| retrieve_hop4 | 1.234 | 1.262 | 1.571 |
| query_hop5 | 0.413 | 0.369 | 0.643 |
| retrieve_hop5 | 1.275 | 1.272 | 1.576 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.049** | **21.428** | **30.312** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 73 |
