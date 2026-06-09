# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.67

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 92.00
- recall: 78.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 3.274 | 2.833 | 6.549 |
| query_hop2 | 0.420 | 0.335 | 1.005 |
| retrieve_hop2 | 1.132 | 1.306 | 1.653 |
| summarize_hop2 | 7.286 | 5.998 | 10.757 |
| query_hop3 | 0.446 | 0.344 | 0.933 |
| retrieve_hop3 | 1.094 | 1.312 | 1.656 |
| summarize_hop3 | 8.182 | 7.325 | 12.606 |
| query_hop4 | 1.565 | 0.443 | 1.144 |
| retrieve_hop4 | 1.383 | 1.375 | 1.685 |
| query_hop5 | 0.591 | 0.488 | 1.002 |
| retrieve_hop5 | 2.393 | 2.605 | 3.303 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **27.773** | **24.807** | **35.285** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 64 |
