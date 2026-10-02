# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- exact_match: 60.67
- f1: 68.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.002 | 0.009 |
| summarize_hop1 | 1.766 | 1.524 | 3.522 |
| query_hop2 | 0.978 | 0.935 | 1.345 |
| retrieve_hop2 | 0.983 | 1.089 | 1.679 |
| summarize_hop2 | 2.681 | 2.577 | 4.405 |
| answer | 1.346 | 1.255 | 2.046 |
| **Total** | **7.775** | **7.446** | **11.547** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
