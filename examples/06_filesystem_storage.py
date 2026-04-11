"""
06 — FilesystemStorage (air-gapped NDJSON).

The reference storage backend for classified and air-gapped
deployments. Writes one NDJSON file per day to a local directory.
Zero network calls. Portable across any platform with a filesystem.

Run:
    python examples/06_filesystem_storage.py
"""

import shutil
import tempfile
from pathlib import Path

from sentinel import DataResidency, Sentinel
from sentinel.storage import FilesystemStorage


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="sentinel-fs-"))
    try:
        sentinel = Sentinel(
            storage=FilesystemStorage(str(tmp)),
            project="fs-demo",
            data_residency=DataResidency.AIR_GAPPED,
            sovereign_scope="EU",
        )

        @sentinel.trace
        def evaluate(item: dict) -> dict:
            return {"status": "ok", "item": item["id"]}

        for i in range(3):
            evaluate({"id": f"item-{i}"})

        # One NDJSON file per day in the storage directory
        ndjson_files = sorted(tmp.glob("*.ndjson"))
        print(f"Wrote {len(ndjson_files)} NDJSON file(s) to {tmp}/")
        for f in ndjson_files:
            lines = f.read_text().strip().splitlines()
            print(f"  {f.name}: {len(lines)} trace line(s)")
            for line in lines[:2]:
                print(f"    {line[:100]}{'...' if len(line) > 100 else ''}")

        # Query works identically to any other backend
        traces = sentinel.query(limit=10)
        print(f"\nQueried {len(traces)} traces")
        print(f"Storage backend: {sentinel.storage.backend_name}")
        print(f"Data residency : {sentinel.data_residency.value}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
