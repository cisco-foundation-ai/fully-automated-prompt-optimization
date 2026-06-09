# Evaluation Summary

Total cases: 300

## Composite Score
- average: 88.67

## Score Breakdown
- num_found: 2.86
- num_gold: 3.00
- partial_recall: 95.44
- recall: 88.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.037 | 0.010 | 0.029 |
| summarize_hop1 | 3.299 | 2.777 | 5.992 |
| query_hop2 | 1.031 | 0.777 | 1.659 |
| retrieve_hop2 | 4.702 | 2.513 | 15.830 |
| summarize_hop2 | 4.595 | 3.700 | 9.713 |
| query_hop3 | 1.202 | 0.895 | 1.869 |
| retrieve_hop3 | 11.823 | 9.977 | 29.231 |
| retrieve_mining | 0.723 | 0.041 | 3.282 |
| title_oracle_llm | 2.369 | 1.123 | 7.779 |
| retrieve_oracle | 1.520 | 0.002 | 6.234 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **31.302** | **28.721** | **58.992** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 34 |
