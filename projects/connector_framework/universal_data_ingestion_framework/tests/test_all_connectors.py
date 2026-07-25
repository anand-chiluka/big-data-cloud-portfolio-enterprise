import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.connectors.sql_connector import SQLConnector, build_demo_sqlite_source
from src.connectors.nosql_connector import NoSQLConnector, build_demo_nosql_source
from src.connectors.api_connector import APIConnector, build_demo_paginated_api
from src.connectors.unstructured_connector import UnstructuredConnector, chunk_text
from src.connectors.batch_file_connector import BatchFileConnector
from src.sinks.base import LocalSink
from src.orchestrator import run_pipeline

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


# ---------- SQL connector ----------

def test_sql_connector_full_extract():
    conn = build_demo_sqlite_source()
    connector = SQLConnector(conn, table_name="customers", cursor_column="updated_at", primary_key="id")
    result = connector.extract()
    assert result.success_count == 3
    assert result.records[0].content_type == "structured"


def test_sql_connector_incremental_extract_uses_cursor():
    conn = build_demo_sqlite_source()
    connector = SQLConnector(conn, table_name="customers", cursor_column="updated_at", primary_key="id")
    first_result = connector.extract()
    assert first_result.success_count == 3

    # Nothing new since last extract: incremental pull should return zero rows
    second_result = connector.extract()
    assert second_result.success_count == 0

    # Insert a new row after the cursor, confirm only the new row comes back
    conn.execute(
        "INSERT INTO customers (id, name, country, updated_at) VALUES (?, ?, ?, ?)",
        (4, "Umbrella Corp", "US", "2026-01-04T00:00:00"),
    )
    conn.commit()
    third_result = connector.extract()
    assert third_result.success_count == 1
    assert third_result.records[0].payload["name"] == "Umbrella Corp"


# ---------- NoSQL connector ----------

def test_nosql_connector_handles_variable_schema():
    collection = build_demo_nosql_source()
    connector = NoSQLConnector(collection, collection_name="events")
    result = connector.extract()
    assert result.success_count == 3
    assert all(r.content_type == "semi_structured" for r in result.records)

    nested_record = next(r for r in result.records if r.record_id == "event_002")
    assert nested_record.payload["metadata"]["device"] == "mobile"
    assert "sku_101" in nested_record.payload["items"]


# ---------- API connector ----------

def test_api_connector_paginates_through_all_pages():
    pages = [
        [{"id": "1", "name": "Acme"}, {"id": "2", "name": "Globex"}],
        [{"id": "3", "name": "Initech"}],
        [],
    ]
    fetch_fn = build_demo_paginated_api(pages)
    connector = APIConnector(fetch_fn, id_field="id")
    result = connector.extract()
    assert result.success_count == 3


def test_api_connector_sync_detects_created_updated_deleted():
    initial_state = {"1": {"id": "1", "name": "Acme", "status": "active"}}
    pages = [
        [
            {"id": "1", "name": "Acme", "status": "churned"},  # updated
            {"id": "2", "name": "Globex", "status": "active"},  # created
        ],
    ]
    fetch_fn = build_demo_paginated_api(pages)
    connector = APIConnector(fetch_fn, id_field="id", previous_state=initial_state)
    result = connector.extract()

    change_types = {r.record_id: r.payload["_sync_change_type"] for r in result.records}
    assert change_types["1"] == "updated"
    assert change_types["2"] == "created"


# ---------- Unstructured connector ----------

def test_chunk_text_respects_sentence_boundaries():
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = chunk_text(text, chunk_size=40, overlap=10)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.strip().endswith((".", "!", "?")) or chunk == chunks[-1]


def test_unstructured_connector_extracts_real_pdf():
    pdf_path = os.path.join(SAMPLE_DATA_DIR, "unstructured", "data_platform_policy.pdf")
    connector = UnstructuredConnector([pdf_path], chunk_size=500, overlap=100)
    result = connector.extract()

    assert result.success_count > 0
    assert result.error_count == 0
    assert all(r.content_type == "unstructured" for r in result.records)

    full_text = " ".join(r.payload["text"] for r in result.records)
    assert "Data Classification" in full_text
    assert "Restricted" in full_text


# ---------- Batch file connector ----------

def test_batch_file_connector_reads_csv_json_and_parquet():
    batch_dir = os.path.join(SAMPLE_DATA_DIR, "batch")
    connector = BatchFileConnector(batch_dir, id_field="id")
    result = connector.extract()

    # 4 products (csv) + 3 vendors (json) + 3 orders (parquet) = 10
    assert result.success_count == 10
    assert result.error_count == 0

    source_ids = {r.record_id for r in result.records}
    assert "p1" in source_ids   # from csv
    assert "v1" in source_ids   # from json
    assert "o1" in source_ids   # from parquet


# ---------- Full orchestrator run: every connector -> one sink ----------

def test_orchestrator_runs_all_connector_types_end_to_end(tmp_path):
    sql_conn = build_demo_sqlite_source()
    sql_connector = SQLConnector(sql_conn, table_name="customers", cursor_column="updated_at", primary_key="id")

    nosql_connector = NoSQLConnector(build_demo_nosql_source(), collection_name="events")

    pages = [[{"id": "1", "name": "Acme"}], []]
    api_connector = APIConnector(build_demo_paginated_api(pages), id_field="id")

    pdf_path = os.path.join(SAMPLE_DATA_DIR, "unstructured", "data_platform_policy.pdf")
    unstructured_connector = UnstructuredConnector([pdf_path], chunk_size=500)

    batch_connector = BatchFileConnector(os.path.join(SAMPLE_DATA_DIR, "batch"), id_field="id")

    sink = LocalSink(str(tmp_path / "output"))

    summaries = run_pipeline(
        [sql_connector, nosql_connector, api_connector, unstructured_connector, batch_connector],
        sink,
    )

    assert len(summaries) == 5
    assert all(s.records_written == s.records_extracted for s in summaries)
    assert sum(s.records_written for s in summaries) > 0

    output_files = list((tmp_path / "output").iterdir())
    assert len(output_files) == 5  # one ndjson file per distinct source


if __name__ == "__main__":
    import tempfile
    test_sql_connector_full_extract()
    test_sql_connector_incremental_extract_uses_cursor()
    test_nosql_connector_handles_variable_schema()
    test_api_connector_paginates_through_all_pages()
    test_api_connector_sync_detects_created_updated_deleted()
    test_chunk_text_respects_sentence_boundaries()
    test_unstructured_connector_extracts_real_pdf()
    test_batch_file_connector_reads_csv_json_and_parquet()
    with tempfile.TemporaryDirectory() as td:
        from pathlib import Path
        test_orchestrator_runs_all_connector_types_end_to_end(Path(td))
    print("All tests passed.")
