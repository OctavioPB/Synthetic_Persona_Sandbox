"""Thin client for the Confluent Schema Registry REST API.

Handles schema registration and lookup. Used by both the producer (to get the
schema_id for the Confluent wire format header) and the consumer (to decode
schema_id → schema for deserialization).

Wire format: [0x00][schema_id: 4 bytes BE][avro_payload]
"""

from __future__ import annotations

import logging
import struct
from io import BytesIO

import fastavro
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_MAGIC_BYTE = b"\x00"
_SCHEMA_ID_FMT = ">I"  # 4-byte big-endian unsigned int


class SchemaRegistryError(Exception):
    pass


class SchemaRegistryClient:
    """Registers Avro schemas and serializes/deserializes using the Confluent wire format.

    Args:
        base_url: Schema Registry base URL (e.g. 'http://localhost:8081').
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._id_to_schema: dict[int, dict] = {}  # type: ignore[type-arg]
        self._subject_to_id: dict[str, int] = {}
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(total=5, backoff_factor=0.5, status_forcelist=[503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def register_schema(self, subject: str, avro_schema: dict) -> int:  # type: ignore[type-arg]
        """Register a schema and return its numeric schema_id.

        Args:
            subject: Schema Registry subject name (typically '<topic>-value').
            avro_schema: Parsed Avro schema dict.

        Returns:
            The schema_id assigned by the registry.

        Raises:
            SchemaRegistryError: If registration fails.
        """
        import json

        url = f"{self._base_url}/subjects/{subject}/versions"
        payload = {"schema": json.dumps(avro_schema)}
        resp = self._session.post(url, json=payload, headers={"Content-Type": "application/vnd.schemaregistry.v1+json"})
        if not resp.ok:
            raise SchemaRegistryError(f"Failed to register schema for '{subject}': {resp.text}")
        schema_id: int = resp.json()["id"]
        self._subject_to_id[subject] = schema_id
        self._id_to_schema[schema_id] = avro_schema
        logger.info("Registered schema '%s' → schema_id=%d", subject, schema_id)
        return schema_id

    def get_schema_by_id(self, schema_id: int) -> dict:  # type: ignore[type-arg]
        """Fetch a schema from the registry by its id (with local cache).

        Args:
            schema_id: Numeric schema id.

        Returns:
            The parsed Avro schema dict.

        Raises:
            SchemaRegistryError: If the schema cannot be fetched.
        """
        import json

        if schema_id in self._id_to_schema:
            return self._id_to_schema[schema_id]

        url = f"{self._base_url}/schemas/ids/{schema_id}"
        resp = self._session.get(url)
        if not resp.ok:
            raise SchemaRegistryError(f"Failed to fetch schema_id={schema_id}: {resp.text}")
        schema = json.loads(resp.json()["schema"])
        self._id_to_schema[schema_id] = schema
        return schema  # type: ignore[return-value]

    # ── Wire format ────────────────────────────────────────────────────────────

    def encode(self, schema_id: int, record: dict, writer_schema: dict) -> bytes:  # type: ignore[type-arg]
        """Serialize a record to Confluent wire-format bytes.

        Args:
            schema_id: The schema id to embed in the header.
            record: The Avro record as a dict.
            writer_schema: The Avro schema to use for serialization.

        Returns:
            Bytes in [magic][schema_id][avro] format.
        """
        buf = BytesIO()
        buf.write(_MAGIC_BYTE)
        buf.write(struct.pack(_SCHEMA_ID_FMT, schema_id))
        fastavro.schemaless_writer(buf, fastavro.parse_schema(writer_schema), record)
        return buf.getvalue()

    def decode(self, data: bytes) -> tuple[int, dict]:  # type: ignore[type-arg]
        """Deserialize Confluent wire-format bytes.

        Args:
            data: Raw bytes from Kafka.

        Returns:
            Tuple of (schema_id, deserialized_record_dict).

        Raises:
            SchemaRegistryError: If the magic byte is wrong or schema is unknown.
        """
        if data[0:1] != _MAGIC_BYTE:
            raise SchemaRegistryError("Invalid Confluent wire-format magic byte")
        schema_id = struct.unpack(_SCHEMA_ID_FMT, data[1:5])[0]
        writer_schema = self.get_schema_by_id(schema_id)
        buf = BytesIO(data[5:])
        record = fastavro.schemaless_reader(buf, fastavro.parse_schema(writer_schema))
        return schema_id, record  # type: ignore[return-value]
