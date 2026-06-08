# Sample Data

This folder demonstrates structured, semi structured, and unstructured input patterns.

| Type | Example | Compression |
| --- | --- | --- |
| Structured | orders CSV | gzip |
| Semi structured | clickstream JSON Lines | bz2 and gzip |
| Unstructured | support notes text | zip |
| Columnar | orders parquet | generated when pyarrow is available |

Run:

```bash
python data/generators/generate_sample_data.py
```
