# Evaluation Summary

Total cases: 300

## Composite Score
- average: 20.67

## Score Breakdown
- num_found: 1.79
- num_gold: 3.00
- num_missing: 1.21
- partial_recall: 59.56
- recall: 20.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 1.790 | 1.555 | 2.485 |
| query_hop2 | 0.820 | 0.665 | 1.073 |
| retrieve_hop2 | 0.557 | 0.002 | 1.538 |
| summarize_hop2 | 1.874 | 1.696 | 2.672 |
| query_hop3 | 0.784 | 0.681 | 0.967 |
| retrieve_hop3 | 0.737 | 1.036 | 1.543 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **6.566** | **5.833** | **13.496** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 238 |
