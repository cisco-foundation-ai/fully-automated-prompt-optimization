# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.65

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.036 | 0.002 | 0.010 |
| summarize_hop1 | 2.039 | 1.864 | 2.865 |
| query_hop2 | 1.271 | 1.110 | 1.821 |
| retrieve_hop2 | 0.574 | 0.005 | 1.595 |
| summarize_hop2 | 1.837 | 1.606 | 2.820 |
| answer | 1.080 | 0.835 | 1.515 |
| **Total** | **6.838** | **6.165** | **9.978** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
