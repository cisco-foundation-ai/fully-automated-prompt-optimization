# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.60

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.009 |
| summarize_hop1 | 1.447 | 1.309 | 2.028 |
| query_hop2 | 1.149 | 1.048 | 1.499 |
| retrieve_hop2 | 0.322 | 0.002 | 1.501 |
| summarize_hop2 | 1.470 | 1.271 | 1.923 |
| answer | 1.092 | 0.937 | 1.949 |
| **Total** | **5.517** | **4.867** | **8.697** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 82 |
