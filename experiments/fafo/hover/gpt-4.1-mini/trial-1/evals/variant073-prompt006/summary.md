# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- num_found: 2.59
- num_gold: 3.00
- partial_recall: 86.33
- recall: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.010 | 0.022 |
| summarize_hop1 | 6.773 | 5.231 | 15.604 |
| query_hop2 | 1.010 | 0.774 | 1.563 |
| retrieve_hop2 | 3.389 | 2.056 | 10.684 |
| summarize_hop2 | 4.991 | 4.543 | 9.006 |
| query_hop3 | 1.338 | 0.922 | 2.595 |
| retrieve_hop3 | 9.185 | 8.201 | 18.177 |
| retrieve_mining | 9.737 | 9.590 | 16.928 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **36.437** | **35.671** | **53.348** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 100 |
