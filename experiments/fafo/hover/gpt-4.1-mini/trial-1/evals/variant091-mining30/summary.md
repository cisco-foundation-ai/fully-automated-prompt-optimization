# Evaluation Summary

Total cases: 75

## Composite Score
- average: 90.67

## Score Breakdown
- num_found: 2.88
- num_gold: 3.00
- partial_recall: 96.00
- recall: 90.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.193 | 0.011 | 1.362 |
| summarize_hop1 | 3.085 | 2.778 | 4.918 |
| query_hop2 | 0.972 | 0.802 | 1.506 |
| retrieve_hop2 | 2.381 | 1.387 | 16.166 |
| summarize_hop2 | 5.114 | 3.852 | 12.522 |
| query_hop3 | 0.968 | 0.833 | 1.528 |
| retrieve_hop3 | 5.097 | 2.665 | 14.220 |
| retrieve_mining | 3.968 | 3.143 | 11.683 |
| title_oracle_llm | 2.755 | 1.087 | 9.133 |
| retrieve_oracle | 1.239 | 0.001 | 7.880 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **25.772** | **23.841** | **44.633** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 7 |
