"""
STAR
Situation: Pub/Sub clickstream events need scalable managed streaming into BigQuery.
Task: Build a non function streaming pipeline using Apache Beam on Dataflow.
Action: Parse messages, validate required fields, route bad records, and write valid events to BigQuery.
Result: Demonstrates production style GCP streaming with managed autoscaling and DLQ design.
"""

from __future__ import annotations

import argparse
import json
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions


class ParseEvent(beam.DoFn):
    """Parse Pub/Sub bytes into dictionaries and tag invalid records."""

    BAD = "bad_records"

    def process(self, element):
        try:
            data = json.loads(element.decode("utf-8"))
            if "event_id" not in data:
                raise ValueError("Missing event_id")
            yield data
        except Exception as exc:
            yield beam.pvalue.TaggedOutput(self.BAD, {"raw": element.decode("utf-8", errors="ignore"), "error": str(exc)})


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_subscription", required=True)
    parser.add_argument("--output_table", required=True)
    parser.add_argument("--bad_table", required=True)
    known_args, pipeline_args = parser.parse_known_args(argv)

    with beam.Pipeline(options=PipelineOptions(pipeline_args, streaming=True)) as pipeline:
        parsed = (
            pipeline
            | "ReadPubSub" >> beam.io.ReadFromPubSub(subscription=known_args.input_subscription)
            | "ParseEvent" >> beam.ParDo(ParseEvent()).with_outputs(ParseEvent.BAD, main="valid")
        )

        parsed.valid | "WriteValidBQ" >> beam.io.WriteToBigQuery(known_args.output_table)
        parsed.bad_records | "WriteBadBQ" >> beam.io.WriteToBigQuery(known_args.bad_table)


if __name__ == "__main__":
    run()
