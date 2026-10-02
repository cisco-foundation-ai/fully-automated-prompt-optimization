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
| retrieve_hop1 | 0.305 | 0.011 | 1.623 |
| summarize_hop1 | 3.321 | 2.824 | 6.390 |
| query_hop2 | 1.005 | 0.788 | 1.836 |
| retrieve_hop2 | 2.071 | 1.570 | 6.470 |
| summarize_hop2 | 4.889 | 3.866 | 9.942 |
| query_hop3 | 0.969 | 0.861 | 1.837 |
| retrieve_hop3 | 5.270 | 1.757 | 18.543 |
| retrieve_mining | 0.219 | 0.037 | 1.596 |
| title_oracle_llm | 2.173 | 1.076 | 6.804 |
| retrieve_oracle | 0.917 | 0.001 | 6.434 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **21.139** | **16.251** | **41.324** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 7 |
