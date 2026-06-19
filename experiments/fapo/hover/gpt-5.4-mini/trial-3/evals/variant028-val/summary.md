# Evaluation Summary

Total cases: 300

## Composite Score
- average: 32.67

## Score Breakdown
- num_found: 2.10
- num_gold: 3.00
- num_missing: 0.90
- partial_recall: 70.00
- recall: 32.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 1.767 | 1.620 | 2.659 |
| query_hop2 | 0.823 | 0.688 | 1.063 |
| retrieve_hop2 | 1.538 | 1.543 | 1.667 |
| summarize_hop2 | 2.316 | 2.022 | 3.323 |
| query_hop3 | 0.798 | 0.671 | 1.147 |
| retrieve_hop3 | 1.423 | 1.554 | 1.665 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.669** | **7.991** | **12.029** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 202 |
