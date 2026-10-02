# Evaluation Summary

Total cases: 300

## Composite Score
- average: 22.67

## Score Breakdown
- num_found: 1.81
- num_gold: 3.00
- num_missing: 1.19
- partial_recall: 60.22
- recall: 22.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.004 |
| summarize_hop1 | 1.702 | 1.573 | 2.378 |
| query_hop2 | 0.779 | 0.736 | 1.183 |
| retrieve_hop2 | 0.735 | 0.009 | 1.610 |
| summarize_hop2 | 1.785 | 1.769 | 2.519 |
| query_hop3 | 0.851 | 0.731 | 1.143 |
| retrieve_hop3 | 0.894 | 1.056 | 1.613 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **6.754** | **6.387** | **8.906** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 232 |
