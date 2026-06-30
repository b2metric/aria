"""upload_csv_stream lazily turns a batch iterator into a CSV byte stream and
hands it to MinIO put_object as a multipart (length=-1) upload."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from agents.artifact_store import ArtifactStore


def _store_with_fake_client():
    store = ArtifactStore(endpoint="minio:9000", bucket="aria-artifacts")
    client = MagicMock()
    client.put_object.return_value = MagicMock(etag="deadbeef")
    store._client = client  # bypass connect()
    return store, client


def test_upload_csv_stream_writes_header_rows_and_coerces_values():
    store, client = _store_with_fake_client()
    batches = [
        [{"id": 1, "amt": Decimal("10.5"), "ts": datetime(2026, 7, 1), "note": None}],
        [{"id": 2, "amt": Decimal("20"), "ts": datetime(2026, 7, 2), "note": "x"}],
    ]
    ref = store.upload_csv_stream(iter(batches), key="exports/ws1/c/data.csv")

    # MinIO multipart: length=-1 + a part_size kwarg.
    _, kwargs = client.put_object.call_args
    assert kwargs["length"] == -1
    assert kwargs["part_size"] >= 5 * 1024 * 1024
    assert kwargs["object_name"] == "exports/ws1/c/data.csv"

    # Drain the stream object that was handed to put_object and parse it back.
    stream = kwargs["data"]
    raw = stream.read()
    text = raw.decode("utf-8")
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert parsed[0] == {"id": "1", "amt": "10.5", "ts": "2026-07-01 00:00:00", "note": ""}
    assert parsed[1]["note"] == "x"
    assert ref.format == "csv"
    assert ref.key == "exports/ws1/c/data.csv"


def test_upload_csv_stream_empty_yields_no_upload():
    store, client = _store_with_fake_client()
    ref = store.upload_csv_stream(iter([]), key="exports/ws1/c/empty.csv")
    assert ref is None
    client.put_object.assert_not_called()


def test_iterator_io_readinto_handles_partial_reads_and_counts_bytes():
    from agents.artifact_store import _IteratorIO

    # chunk (5 bytes) larger than the read buffer (2 bytes) → leftover must persist.
    stream = _IteratorIO(iter([b"abcde", b"fg"]))
    out = bytearray()
    while True:
        chunk = stream.read(2)  # RawIOBase.read(n) → readinto on a fresh 2-byte buffer
        if not chunk:
            break
        out += chunk
    assert bytes(out) == b"abcdefg"
    assert stream.bytes_read == 7


def test_upload_csv_stream_size_bytes_reflects_drained_stream():
    """A put_object that actually drains the stream (like the real SDK) → size_bytes > 0."""
    store, client = _store_with_fake_client()

    def _draining_put_object(*, data, **kw):
        while data.read(4):  # chunked drain, mirrors MinIO read_part_data
            pass
        return MagicMock(etag="deadbeef")

    client.put_object.side_effect = _draining_put_object
    ref = store.upload_csv_stream(iter([[{"a": 1, "b": 2}]]), key="exports/x.csv")
    assert ref is not None
    assert ref.size_bytes > 0  # header + one row actually counted
