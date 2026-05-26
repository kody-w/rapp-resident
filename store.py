"""Durable append-only room storage. Azure Table Storage in the cloud (the function's
own storage account — no extra resource), a local JSONL file when running off-Azure so
the same code is testable without any cloud."""

import json
import os
import threading

try:
    from azure.data.tables import TableServiceClient
    from azure.core.exceptions import ResourceExistsError
    _HAS_TABLES = True
except Exception:
    _HAS_TABLES = False

TABLE = "rappresident"


def _conn() -> str:
    return os.environ.get("AzureWebJobsStorage", "")


def _use_table() -> bool:
    c = _conn()
    return _HAS_TABLES and bool(c) and "UseDevelopmentStorage" not in c


class _TableStore:
    def __init__(self):
        svc = TableServiceClient.from_connection_string(_conn())
        svc.create_table_if_not_exists(TABLE)
        self.t = svc.get_table_client(TABLE)

    def read(self, room, since=0):
        ents = self.t.query_entities(f"PartitionKey eq '{room}'")
        evs = sorted((json.loads(e["Body"]) for e in ents), key=lambda e: e.get("ts", ""))
        return evs[since:] if since else evs

    def append(self, room, ev, rid):
        try:
            self.t.create_entity({"PartitionKey": room,
                                  "RowKey": f"{ev.get('ts', '')}-{rid}",
                                  "Body": json.dumps(ev)})
        except ResourceExistsError:
            pass  # idempotent — same event posted twice is a no-op


class _FileStore:
    def __init__(self):
        self.dir = os.environ.get("RESIDENT_DATA", "/tmp/rapp-resident-data")
        os.makedirs(self.dir, exist_ok=True)
        self.lock = threading.Lock()

    def _p(self, room):
        return os.path.join(self.dir, room.replace("/", "_") + ".jsonl")

    def _records(self, room):
        p = self._p(room)
        if not os.path.exists(p):
            return []
        return [json.loads(line) for line in open(p) if line.strip()]

    def read(self, room, since=0):
        # records wrap the pristine event so the stored event stays byte-identical
        # to what was signed (adding fields would break verification)
        evs = [rec["ev"] for rec in self._records(room)]
        return evs[since:] if since else evs

    def append(self, room, ev, rid):
        with self.lock:
            if any(rec.get("id") == rid for rec in self._records(room)):
                return  # idempotent
            with open(self._p(room), "a") as f:
                f.write(json.dumps({"id": rid, "ev": ev}) + "\n")


def store():
    return _TableStore() if _use_table() else _FileStore()
