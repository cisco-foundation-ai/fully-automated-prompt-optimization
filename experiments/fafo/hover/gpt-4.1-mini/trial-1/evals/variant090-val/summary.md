# Evaluation Summary

Total cases: 300

## Composite Score
- average: 90.33

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- partial_recall: 96.44
- recall: 90.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.722 | 0.019 | 3.148 |
| summarize_hop1 | 3.206 | 2.590 | 6.432 |
| query_hop2 | 1.015 | 0.805 | 1.997 |
| retrieve_hop2 | 2.270 | 1.438 | 7.447 |
| summarize_hop2 | 4.503 | 3.447 | 9.821 |
| query_hop3 | 1.164 | 0.879 | 2.042 |
| retrieve_hop3 | 8.105 | 6.331 | 22.082 |
| retrieve_mining | 0.101 | 0.042 | 0.071 |
| title_oracle_llm | 3.062 | 1.112 | 11.256 |
| retrieve_oracle | 1.622 | 0.002 | 7.590 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **25.771** | **22.576** | **48.526** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 29 |
