# Evaluation Summary

Total cases: 75

## Composite Score
- average: 90.67

## Score Breakdown
- num_found: 2.87
- num_gold: 3.00
- partial_recall: 95.56
- recall: 90.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.010 | 0.205 |
| summarize_hop1 | 4.370 | 2.786 | 12.705 |
| query_hop2 | 0.966 | 0.733 | 2.254 |
| retrieve_hop2 | 2.792 | 1.573 | 13.348 |
| summarize_hop2 | 4.174 | 3.827 | 8.156 |
| query_hop3 | 1.012 | 0.847 | 2.263 |
| retrieve_hop3 | 5.109 | 3.321 | 12.789 |
| retrieve_mining | 0.062 | 0.039 | 0.086 |
| title_oracle_llm | 1.138 | 0.897 | 2.658 |
| retrieve_oracle | 0.194 | 0.000 | 2.641 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **19.843** | **18.494** | **40.416** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 7 |
