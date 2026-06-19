# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 75.05

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.007 |
| summarize_hop1 | 1.195 | 1.151 | 1.650 |
| query_hop2 | 1.061 | 0.965 | 1.365 |
| retrieve_hop2 | 0.512 | 0.002 | 1.627 |
| summarize_hop2 | 1.230 | 1.153 | 1.679 |
| answer | 1.072 | 0.867 | 1.472 |
| **Total** | **5.098** | **4.459** | **7.045** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
| query_hop2 | 1 |
