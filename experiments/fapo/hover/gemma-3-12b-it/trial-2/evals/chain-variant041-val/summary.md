# Evaluation Summary

Total cases: 300

## Composite Score
- average: 80.67

## Score Breakdown
- num_found: 2.78
- num_gold: 3.00
- num_missing: 0.22
- partial_recall: 92.56
- recall: 80.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 3.483 | 2.971 | 7.050 |
| query_hop2 | 0.475 | 0.331 | 1.588 |
| retrieve_hop2 | 0.782 | 0.154 | 1.612 |
| summarize_hop2 | 6.944 | 5.832 | 10.489 |
| query_hop3 | 0.547 | 0.372 | 1.462 |
| retrieve_hop3 | 2.770 | 2.915 | 3.242 |
| summarize_hop3 | 9.401 | 8.152 | 16.126 |
| query_hop4 | 0.538 | 0.424 | 1.382 |
| retrieve_hop4 | 1.332 | 1.482 | 1.667 |
| query_hop5 | 0.633 | 0.470 | 1.382 |
| retrieve_hop5 | 2.073 | 2.071 | 3.239 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.982** | **26.849** | **37.931** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 58 |
