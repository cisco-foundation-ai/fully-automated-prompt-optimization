# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- partial_recall: 88.22
- recall: 69.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.006 |
| summarize_hop1 | 2.308 | 2.104 | 3.639 |
| query_hop2 | 0.772 | 0.677 | 1.003 |
| retrieve_hop2 | 0.775 | 0.004 | 1.650 |
| summarize_hop2 | 3.509 | 3.103 | 5.789 |
| query_hop3 | 0.697 | 0.641 | 1.030 |
| retrieve_hop3 | 1.117 | 1.119 | 1.657 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.187** | **8.654** | **13.420** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 91 |
