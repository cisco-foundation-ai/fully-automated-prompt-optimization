# Evaluation Summary

Total cases: 300

## Composite Score
- average: 42.67

## Score Breakdown
- num_found: 2.30
- num_gold: 3.00
- num_missing: 0.70
- partial_recall: 76.78
- recall: 42.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_claim | 0.004 | 0.002 | 0.013 |
| query_gen | 0.852 | 0.758 | 1.249 |
| parse_queries | 0.000 | 0.000 | 0.000 |
| retrieve_q1 | 0.773 | 0.003 | 1.641 |
| retrieve_q2 | 0.505 | 0.002 | 1.627 |
| retrieve_q3 | 0.535 | 0.002 | 1.614 |
| combine_retrievals | 0.001 | 0.001 | 0.001 |
| **Total** | **2.671** | **1.992** | **5.703** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_q3 | 164 |
| query_3 | 18 |
| query_2 | 10 |
| retrieve_q1 | 10 |
| retrieve_q2 | 10 |
