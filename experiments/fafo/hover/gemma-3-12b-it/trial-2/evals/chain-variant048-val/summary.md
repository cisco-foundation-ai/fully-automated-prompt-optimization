# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.67

## Score Breakdown
- num_found: 2.78
- num_gold: 3.00
- num_missing: 0.22
- partial_recall: 92.56
- recall: 79.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.981 | 0.550 | 1.677 |
| summarize_hop1 | 3.869 | 2.732 | 5.801 |
| query_hop2 | 0.358 | 0.331 | 0.431 |
| retrieve_hop2 | 0.623 | 0.002 | 1.606 |
| summarize_hop2 | 5.787 | 5.570 | 9.264 |
| query_hop3 | 0.426 | 0.382 | 0.552 |
| retrieve_hop3 | 1.549 | 1.539 | 3.146 |
| summarize_hop3 | 6.700 | 6.359 | 11.340 |
| query_hop4 | 0.373 | 0.337 | 0.577 |
| retrieve_hop4 | 1.285 | 1.456 | 1.640 |
| query_hop5 | 0.515 | 0.456 | 0.773 |
| retrieve_hop5 | 1.884 | 1.623 | 3.191 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.351** | **23.007** | **31.347** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 61 |
