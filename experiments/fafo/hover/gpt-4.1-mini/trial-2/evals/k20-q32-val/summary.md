# Evaluation Summary

Total cases: 300

## Composite Score
- average: 27.67

## Score Breakdown
- num_found: 1.98
- num_gold: 3.00
- partial_recall: 65.89
- recall: 27.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.008 |
| summarize_hop1 | 4.551 | 4.021 | 8.527 |
| query_hop2 | 0.937 | 0.605 | 2.359 |
| retrieve_hop2 | 0.223 | 0.002 | 1.467 |
| summarize_hop2 | 4.905 | 4.282 | 9.063 |
| query_hop3 | 0.785 | 0.599 | 1.539 |
| retrieve_hop3 | 0.514 | 0.002 | 1.520 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.934** | **10.802** | **19.352** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 217 |
