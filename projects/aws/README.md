# AWS Big Data Projects

STAR

**Situation:** Hiring teams want proof of hands on cloud data engineering across batch, streaming, serverless, and non serverless systems.

**Task:** Build AWS specific examples without mixing services from other cloud providers.

**Action:** This folder uses only AWS services: S3, Glue, EMR, Kinesis, MSK, Lambda, CloudWatch. Shared technologies such as Kafka, PySpark, Flink, Python, Java, and Snowflake are included only where they integrate naturally.

**Result:** The folder can be reviewed independently for AWS roles and demonstrates cloud native architecture discipline.

## Included Implementations

| Mode | Serverless | Folder | What it shows |
| --- | --- | --- | --- |
| Batch | No | `batch/without_serverless` | Managed Spark ETL with quality gates |
| Batch | Yes | `batch/with_serverless` | Function triggered orchestration |
| Real time | No | `realtime/without_serverless` | Stateful or micro batch streaming |
| Real time | Yes | `realtime/with_serverless` | Lightweight event enrichment and routing |

## Interview Talking Point

I kept the architecture cloud isolated. This avoids the common portfolio mistake of mixing AWS Lambda with Azure Event Hubs or GCP Pub/Sub in one design. The shared concepts remain portable, but each implementation respects the target cloud's native control plane.
