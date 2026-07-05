from __future__ import annotations

import json
import os
from pathlib import Path

from .settle import _dotenv_token, fetch_and_record


def settle_manifest(root: Path) -> dict:
    manifest = json.loads((root / "data/manifests/active-fused-samples.json").read_text())
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN") or _dotenv_token(root / ".env")
    if not token: raise ValueError("FOOTBALL_DATA_API_TOKEN is required")
    settled, waiting, unmatched = [], [], []
    store = root / "data/evaluations/fused-observations.json"
    saved_before = json.loads(store.read_text()) if store.exists() else {"observations": []}
    recorded = {row["external_match_id"] for row in saved_before["observations"] if row["model"] == "fused-v2"}
    for record in manifest["records"]:
        match_id = record.get("football_data_match_id")
        if not match_id:
            unmatched.append(record["event_id"]); continue
        if match_id in recorded:
            settled.append(match_id); continue
        result = fetch_and_record(match_id, root / record["report"], store, token)
        (settled if result else waiting).append(match_id)
    saved = json.loads(store.read_text()) if store.exists() else {"observations": []}
    return {"settled": settled, "waiting": waiting, "unmatched": unmatched,
            "sample_size": sum(row["model"] == "fused-v2" for row in saved["observations"])}


def main() -> None:
    print(json.dumps(settle_manifest(Path.cwd()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
