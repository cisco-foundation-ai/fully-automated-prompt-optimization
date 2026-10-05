# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.00

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 92.00
- recall: 78.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.012 |
| summarize_hop1 | 3.452 | 2.988 | 6.821 |
| query_hop2 | 0.444 | 0.335 | 1.174 |
| retrieve_hop2 | 0.952 | 1.251 | 1.587 |
| summarize_hop2 | 7.798 | 6.235 | 10.883 |
| query_hop3 | 0.544 | 0.386 | 1.515 |
| retrieve_hop3 | 2.420 | 2.603 | 3.158 |
| summarize_hop3 | 9.296 | 8.038 | 15.345 |
| query_hop4 | 0.623 | 0.429 | 1.741 |
| retrieve_hop4 | 1.328 | 1.422 | 1.625 |
| query_hop5 | 0.670 | 0.477 | 1.927 |
| retrieve_hop5 | 2.011 | 1.643 | 3.149 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **29.542** | **26.909** | **38.719** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 66 |
