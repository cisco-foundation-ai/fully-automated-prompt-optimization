# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- partial_recall: 89.89
- recall: 72.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.004 |
| summarize_hop1 | 2.422 | 2.129 | 4.141 |
| query_hop2 | 0.766 | 0.688 | 1.216 |
| retrieve_hop2 | 0.762 | 0.003 | 1.650 |
| summarize_hop2 | 3.216 | 2.891 | 5.028 |
| query_hop3 | 0.971 | 0.768 | 1.458 |
| retrieve_hop3 | 0.938 | 1.085 | 1.665 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.079** | **8.373** | **14.342** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 82 |
