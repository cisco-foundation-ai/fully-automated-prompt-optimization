# Evaluation Summary

Total cases: 300

## Composite Score
- average: 26.67

## Score Breakdown
- num_found: 1.96
- num_gold: 3.00
- partial_recall: 65.22
- recall: 26.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.004 |
| summarize_hop1 | 3.723 | 3.205 | 6.034 |
| query_hop2 | 0.797 | 0.542 | 1.049 |
| retrieve_hop2 | 0.280 | 0.002 | 1.474 |
| summarize_hop2 | 3.768 | 3.432 | 5.986 |
| query_hop3 | 0.798 | 0.562 | 1.043 |
| retrieve_hop3 | 0.566 | 0.002 | 1.518 |
| retrieve_hop3b | 0.211 | 0.002 | 1.543 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.162** | **9.076** | **17.891** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3b | 220 |
