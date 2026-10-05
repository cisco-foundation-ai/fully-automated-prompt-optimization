# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.67

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- partial_recall: 92.00
- recall: 79.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 2.898 | 2.567 | 4.872 |
| query_hop2 | 0.890 | 0.762 | 1.424 |
| retrieve_hop2 | 1.482 | 1.545 | 1.712 |
| summarize_hop2 | 4.243 | 3.714 | 7.628 |
| query_hop3 | 1.169 | 0.879 | 3.128 |
| retrieve_hop3 | 0.788 | 1.066 | 1.686 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.476** | **10.883** | **17.774** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 61 |
