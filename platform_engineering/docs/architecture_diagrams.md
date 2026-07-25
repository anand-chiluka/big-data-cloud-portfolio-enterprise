# Architecture Diagrams

These diagrams use [Mermaid](https://mermaid.js.org/) syntax, which GitHub
renders natively as real diagrams directly in this Markdown file, no
external image hosting or screenshots required.

## 1. Overall platform architecture (how every project in this repo fits together)

```mermaid
flowchart TB
    subgraph Sources["Data Sources"]
        SQL[("Traditional/Cloud SQL<br/>PostgreSQL, SQL Server,<br/>Oracle, Aurora, Azure SQL")]
        NoSQL[("NoSQL<br/>MongoDB, DynamoDB,<br/>Cassandra, Cosmos DB")]
        API["REST APIs<br/>CRM, ERP, SaaS"]
        Unstruct["Unstructured<br/>PDFs, docs, scans"]
        Batch["Batch Files<br/>CSV, JSON, Parquet"]
        Kafka["Kafka Event Streams<br/>real-time transactions"]
    end

    subgraph Ingestion["Ingestion Layer"]
        Connectors["Universal Connector Framework<br/>(common ExtractedRecord envelope)"]
        RiskPipeline["Kafka Risk Pipeline<br/>(schema validation, enrichment)"]
    end

    subgraph Governance["Governance Layer"]
        PII["PII Detection & Masking"]
        RBAC["RBAC Authorization"]
        Audit["Audit Logging"]
    end

    subgraph Observability["Observability Layer"]
        Metrics["Metrics Registry"]
        SLO["SLO Monitoring"]
        Logs["Structured Logging"]
    end

    subgraph Sinks["Cloud Destinations"]
        SF[("Snowflake")]
        AWS[("AWS S3/Redshift")]
        GCP[("GCP BigQuery")]
        AZ[("Azure ADLS/Synapse")]
    end

    subgraph Consumption["Downstream Consumption"]
        DBT["dbt: staging -> intermediate -> marts"]
        MRR["Governed MRR Metrics"]
        BI["BI Dashboards"]
        RAG["RAG / Vector Search"]
    end

    SQL --> Connectors
    NoSQL --> Connectors
    API --> Connectors
    Unstruct --> Connectors
    Batch --> Connectors
    Kafka --> RiskPipeline

    Connectors --> PII
    RiskPipeline --> PII
    PII --> RBAC
    RBAC --> Audit

    Connectors -.instruments.-> Metrics
    RiskPipeline -.instruments.-> Metrics
    Metrics --> SLO

    Audit --> SF
    Audit --> AWS
    Audit --> GCP
    Audit --> AZ

    SF --> DBT
    DBT --> MRR
    MRR --> BI
    SF --> RAG

    style Sources fill:#e8f0fe
    style Governance fill:#fce8e8
    style Observability fill:#e8fce9
    style Sinks fill:#fff4e5
```

## 2. Real-time risk pipeline data flow

```mermaid
sequenceDiagram
    participant K as Kafka Topic
    participant V as Schema Validator
    participant DQ as Data Quality Gate
    participant R as Risk Enricher
    participant SF as Snowflake Sink
    participant M as Data Quality Monitor
    participant DLQ as Dead Letter Queue

    K->>V: raw transaction event
    alt schema valid
        V->>DQ: validated event
        alt passes quality checks
            DQ->>R: clean event
            R->>R: compute velocity + amount z-score
            R->>SF: enriched event (idempotent upsert)
        else fails quality checks
            DQ->>DLQ: reject with reason code
        end
    else schema invalid
        V->>DLQ: reject with reason code
    end

    loop every 15 minutes
        M->>SF: check freshness, volume, schema drift, reject rate
        M->>M: log pass/fail to data_quality_log
    end
```

## 3. dbt staging -> intermediate -> marts lineage

```mermaid
flowchart LR
    RawEvents[("raw.subscription_events")]
    RawCustomers[("raw.customers")]

    StgEvents["stg_subscription_events"]
    StgCustomers["stg_customers"]

    IntState["int_subscription_current_state<br/>(business logic: computed once)"]

    MartMRR["mart_customer_mrr<br/>(governed per-customer metric)"]
    MartSummary["mart_company_mrr_summary<br/>(single governed company number)"]

    RawEvents --> StgEvents
    RawCustomers --> StgCustomers
    StgEvents --> IntState
    StgCustomers --> IntState
    IntState --> MartMRR
    StgCustomers --> MartMRR
    MartMRR --> MartSummary

    style IntState fill:#fff4e5
    style MartMRR fill:#e8fce9
    style MartSummary fill:#e8fce9
```

## 4. AWS -> Snowflake ingestion path

```mermaid
flowchart LR
    App["Upstream App /<br/>API Gateway / Kinesis"]
    Lambda["Lambda:<br/>validate + convert to Parquet"]
    S3[("S3 landing zone<br/>partitioned by date")]
    SQS["SQS notification queue"]
    Pipe["Snowpipe<br/>(auto-ingest)"]
    Table[("raw.transaction_events")]
    Monitor["monitoring.pipe_ingestion_health"]

    App --> Lambda
    Lambda -->|Parquet| S3
    S3 -->|ObjectCreated event| SQS
    SQS -->|triggers| Pipe
    Pipe --> Table
    Table -.-> Monitor
```

## 5. Governance and access control flow

```mermaid
flowchart TD
    Record["Incoming Record"]
    Scan["scan_record_for_pii()"]
    Classify["classify_record()"]

    Record --> Scan
    Scan --> Classify

    Classify -->|no PII found| Internal["Classification: INTERNAL"]
    Classify -->|PII detected| Restricted["Classification: RESTRICTED"]
    Classify -->|health context| RestrictedHealth["Classification: RESTRICTED_HEALTH"]

    Internal --> Access{"authorize_read(role, classification)"}
    Restricted --> Access
    RestrictedHealth --> Access

    Access -->|role not permitted| Denied["AccessDeniedError"]
    Access -->|role permitted| Filter["filter_columns_for_role()<br/>(strip denylisted columns)"]

    Filter --> AuditLog["AuditLog.record_access()"]
    Denied --> AuditLog

    AuditLog --> Check["restricted_access_without_reason()<br/>compliance check"]

    style Restricted fill:#fce8e8
    style RestrictedHealth fill:#fce8e8
    style Denied fill:#fce8e8
```

## 6. CI/CD pipeline stages

```mermaid
flowchart LR
    PR["Pull Request /<br/>Push to main"]
    Lint["Lint<br/>(ruff, black)"]
    Test["Test<br/>(pytest, coverage >= 80%)"]
    Sec["Security Scan<br/>(pip-audit, trufflehog)"]
    Build["Build & Push<br/>(Docker image)"]
    Deploy["Deploy to K8s<br/>(main branch only,<br/>manual approval)"]

    PR --> Lint
    Lint --> Test
    Lint --> Sec
    Test --> Build
    Sec --> Build
    Build --> Deploy

    style Lint fill:#e8f0fe
    style Test fill:#e8f0fe
    style Sec fill:#fce8e8
    style Build fill:#fff4e5
    style Deploy fill:#e8fce9
```
