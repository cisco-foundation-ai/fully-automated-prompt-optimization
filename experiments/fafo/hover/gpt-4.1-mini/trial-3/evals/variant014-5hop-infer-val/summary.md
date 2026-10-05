# Evaluation Summary

Total cases: 300

## Composite Score
- average: 97.67

## Score Breakdown
- num_found: 2.98
- num_gold: 3.00
- partial_recall: 99.22
- recall: 97.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.986 | 0.536 | 1.677 |
| summarize_hop1 | 30.383 | 25.902 | 60.689 |
| query_hop2 | 1.322 | 1.088 | 1.936 |
| retrieve_hop2 | 9.926 | 10.283 | 12.501 |
| summarize_hop2 | 31.293 | 26.016 | 54.954 |
| query_hop3 | 1.246 | 1.073 | 1.925 |
| retrieve_hop3 | 8.624 | 8.770 | 11.798 |
| summarize_hop3 | 32.155 | 26.901 | 53.478 |
| query_hop4 | 1.845 | 1.496 | 3.738 |
| retrieve_hop4 | 10.053 | 10.114 | 14.442 |
| summarize_hop4 | 42.725 | 36.172 | 73.021 |
| query_hop5 | 2.152 | 1.935 | 3.356 |
| retrieve_hop5 | 15.342 | 15.315 | 21.174 |
| combine_retrievals | 0.010 | 0.009 | 0.018 |
| **Total** | **188.062** | **178.187** | **271.314** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 7 |
