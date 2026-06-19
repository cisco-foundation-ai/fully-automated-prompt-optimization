# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- exact_match: 58.33
- f1: 66.21

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.008 |
| summarize_hop1 | 2.242 | 1.828 | 3.945 |
| query_hop2 | 3.100 | 1.120 | 2.141 |
| retrieve_hop2 | 1.235 | 1.280 | 1.589 |
| summarize_hop2 | 4.144 | 1.591 | 2.742 |
| answer | 1.107 | 0.941 | 1.844 |
| **Total** | **11.832** | **6.658** | **12.541** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 125 |
