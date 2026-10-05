# Evaluation Summary

Total cases: 300

## Composite Score
- average: 28.67

## Score Breakdown
- num_found: 2.04
- num_gold: 3.00
- partial_recall: 67.89
- recall: 28.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.008 |
| summarize_hop1 | 3.879 | 3.040 | 5.827 |
| query_hop2 | 0.861 | 0.548 | 1.546 |
| retrieve_hop2 | 0.480 | 0.002 | 1.597 |
| summarize_hop2 | 3.705 | 3.183 | 6.860 |
| query_hop3 | 0.721 | 0.555 | 1.270 |
| retrieve_hop3 | 0.910 | 1.058 | 1.641 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.565** | **9.265** | **19.167** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 214 |
