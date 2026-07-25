# Platform Engineering Layer

## Why this exists as its own layer, not scattered across projects

Observability, governance, CI/CD, and deployment are cross-cutting
concerns: every project in this repo needs them, and reimplementing each
one per-project is exactly the kind of duplicated effort a platform team
exists to prevent. This directory is the shared infrastructure every
other project in this repo builds on, or would build on in a real
deployment, mirroring how platform engineering actually works at
companies operating at scale (see the Block, Faire, and Airbnb-context
platform engineering framing throughout this portfolio's resume work:
"build the self-service tooling other teams build on" is the whole
premise of this directory).

## What's in here

```
platform_engineering/
  observability/
    src/metrics.py        # structured logging + counter/gauge/histogram metrics registry
    src/slo.py             # executable SLI/SLO definitions and pass/fail checks
    tests/                 # 8/8 passing
  governance/
    src/pii.py              # PII detection (pattern + field-name based) and masking
    src/rbac.py              # role-based access control with column-level filtering
    src/audit.py              # audit trail logging with compliance gap detection
    tests/                     # 16/16 passing
  docker/
    Dockerfile                 # multi-stage, non-root, health-checked
    docker-compose.yml          # local Kafka + pipeline dev stack
  kubernetes/
    deployment.yaml               # streaming consumer: Deployment + Service + HPA
    cronjob.yaml                   # scheduled batch connectors
    configmap_and_secret.yaml       # config + secrets template
  ci_cd/
    github_actions_ci_cd.yml         # lint -> test -> security scan -> build -> deploy
  docs/
    architecture_diagrams.md          # 6 Mermaid diagrams, render natively on GitHub
    mvp_vs_production.md               # concrete gap analysis, every project, every concern
    performance_and_observability.md    # metric naming convention, golden signals, SLOs
    scalability_and_ai_readiness.md      # AI-readiness definition + 10x/100x/1000x scaling plan
    portfolio_roadmap.md                  # honest inventory + where to invest next
```

## What has been validated, and how

**Actually run, with passing tests:**
- `observability/`: 8/8 tests passing, including a genuine bug caught and
  fixed during development (a label-key mismatch between `gauge()` and
  `latest_gauge()` that the test suite caught before this README was even
  written, a real example of tests doing their job)
- `governance/`: 16/16 tests passing, covering PII detection (both
  pattern-based and field-name-based), masking (both partial-redaction
  and irreversible-hash strategies), RBAC authorization and column
  filtering, and audit log compliance-gap detection

**Syntax-validated but not executed against live infrastructure**, since
no Docker daemon, Kubernetes cluster, or GitHub Actions runner exists in
this development environment:
- `docker-compose.yml` and all three Kubernetes manifest files: parsed
  and validated with PyYAML, confirmed correct `apiVersion`/`kind`/
  `metadata` structure across all 6 K8s resources
- `github_actions_ci_cd.yml`: parsed and validated, confirmed the job
  dependency chain (`lint -> test/security_scan -> build -> deploy`)
  resolves correctly
- `Dockerfile`: standard multi-stage syntax, not built in this
  environment (no Docker daemon available)

## How this connects to the rest of the repo

- `observability/src/metrics.py` is the library every connector in
  `universal_data_ingestion_framework/` and `kafka_snowflake_risk_pipeline/`
  would import in production, replacing their current plain
  `logging.info()` calls with structured, queryable metrics.
- `governance/src/pii.py` and `rbac.py` are designed to sit directly in
  front of every sink, classifying and filtering records the same way
  regardless of whether they came from `SQLConnector`, `NoSQLConnector`,
  or `UnstructuredConnector`.
- The Dockerfile and Kubernetes manifests target
  `kafka_snowflake_risk_pipeline/` specifically as the example, since
  it's the one always-on streaming service in this repo; the batch
  connectors in the universal framework map to the `CronJob` pattern
  instead.

See `docs/architecture_diagrams.md` for how all of this fits together
visually, and `docs/mvp_vs_production.md` for the honest, specific answer
to "what would you do differently at scale" for every project in this
repository.
