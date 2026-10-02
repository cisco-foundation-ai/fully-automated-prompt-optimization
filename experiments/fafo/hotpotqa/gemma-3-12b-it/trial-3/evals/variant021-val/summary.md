# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.67

## Score Breakdown
- exact_match: 58.67
- f1: 67.43

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.010 |
| summarize_hop1 | 2.929 | 1.772 | 3.325 |
| query_hop2 | 1.017 | 0.994 | 1.472 |
| retrieve_hop2 | 0.570 | 0.003 | 1.597 |
| summarize_hop2 | 4.274 | 3.153 | 5.052 |
| answer | 0.888 | 0.859 | 1.271 |
| **Total** | **9.700** | **7.336** | **10.981** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 124 |
