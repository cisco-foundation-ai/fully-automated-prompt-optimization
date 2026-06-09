# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- partial_recall: 90.33
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.007 | 0.002 | 0.009 |
| summarize_hop1 | 2.840 | 2.522 | 4.723 |
| query_hop2 | 0.840 | 0.755 | 1.393 |
| retrieve_hop2 | 0.681 | 0.003 | 1.582 |
| summarize_hop2 | 3.893 | 3.424 | 6.621 |
| query_hop3 | 0.872 | 0.774 | 1.661 |
| retrieve_hop3 | 0.372 | 0.002 | 1.551 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.506** | **8.925** | **15.105** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 76 |
