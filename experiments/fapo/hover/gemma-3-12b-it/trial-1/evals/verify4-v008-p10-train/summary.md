# Evaluation Summary

Total cases: 150

## Composite Score
- average: 88.67

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- num_missing: 0.11
- partial_recall: 96.22
- recall: 88.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.921 | 0.032 | 7.425 |
| summarize_hop1 | 1.639 | 1.309 | 3.512 |
| retrieve_hop2 | 3.803 | 3.296 | 8.142 |
| summarize_hop2 | 1.449 | 1.326 | 2.641 |
| retrieve_hop3 | 2.898 | 2.142 | 6.529 |
| summarize_hop3 | 1.398 | 1.179 | 2.629 |
| retrieve_hop4 | 2.135 | 1.650 | 4.872 |
| combine_retrievals | 0.020 | 0.019 | 0.041 |
| **Total** | **15.264** | **14.978** | **26.552** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 17 |
