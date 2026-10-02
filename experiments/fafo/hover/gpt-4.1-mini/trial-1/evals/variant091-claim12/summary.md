# Evaluation Summary

Total cases: 75

## Composite Score
- average: 89.33

## Score Breakdown
- num_found: 2.85
- num_gold: 3.00
- partial_recall: 95.11
- recall: 89.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.522 | 0.013 | 1.573 |
| summarize_hop1 | 3.553 | 2.812 | 7.874 |
| query_hop2 | 0.956 | 0.790 | 1.880 |
| retrieve_hop2 | 2.139 | 1.371 | 9.782 |
| summarize_hop2 | 5.264 | 4.089 | 13.983 |
| query_hop3 | 0.900 | 0.774 | 1.316 |
| retrieve_hop3 | 4.040 | 2.207 | 12.940 |
| retrieve_mining | 0.039 | 0.038 | 0.065 |
| title_oracle_llm | 2.634 | 0.971 | 9.141 |
| retrieve_oracle | 0.957 | 0.001 | 7.745 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **21.003** | **19.088** | **41.923** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
