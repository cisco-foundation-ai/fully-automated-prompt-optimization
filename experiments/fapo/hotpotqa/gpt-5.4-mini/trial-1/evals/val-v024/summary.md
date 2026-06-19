# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.120 | 0.002 | 0.117 |
| summarize_hop1 | 1.307 | 1.211 | 2.002 |
| query_hop2 | 1.106 | 1.030 | 1.767 |
| retrieve_hop2 | 0.454 | 0.002 | 1.598 |
| summarize_hop2 | 1.531 | 1.447 | 2.387 |
| answer | 0.786 | 0.673 | 1.043 |
| **Total** | **5.304** | **4.601** | **7.756** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
