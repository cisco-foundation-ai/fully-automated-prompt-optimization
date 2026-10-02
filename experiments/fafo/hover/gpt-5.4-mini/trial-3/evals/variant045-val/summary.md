# Evaluation Summary

Total cases: 300

## Composite Score
- average: 54.67

## Score Breakdown
- num_found: 2.48
- num_gold: 3.00
- num_missing: 0.52
- partial_recall: 82.56
- recall: 54.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.006 | 0.002 | 0.004 |
| summarize_hop1 | 2.683 | 2.361 | 4.580 |
| query_hop2 | 0.827 | 0.697 | 1.271 |
| retrieve_hop2 | 1.549 | 1.549 | 1.706 |
| summarize_hop2 | 3.127 | 2.639 | 5.828 |
| query_hop3 | 0.853 | 0.706 | 1.388 |
| retrieve_hop3 | 1.524 | 1.564 | 1.697 |
| combine_retrievals | 0.001 | 0.001 | 0.001 |
| **Total** | **10.571** | **9.934** | **15.274** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 136 |
