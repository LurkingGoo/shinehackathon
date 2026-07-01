"""Contract schema — one inspectable artifact + the anti-drift source.

`models.py` mirrors triage-dashboard/lib/types.ts by hand. To stop the two from
silently diverging (the entire risk surface of the seam), this module:

1. Emits a JSON Schema for each endpoint payload from the pydantic models
   (`contract.schema.json`), which live responses are validated against in tests.
2. Is paired with tests/test_contract.py::test_models_match_types_ts, which
   parses types.ts and asserts field-name parity with these models.

Regenerate the artifact after any model change:  python -m app.contract
(the doc-ritual + a staleness test enforce this).
"""
from __future__ import annotations

import json
from pathlib import Path

from app import models

# endpoint payload → model. Each model's JSON Schema is self-contained ($defs
# for nested types are inlined by pydantic), so validation needs no stitching.
PAYLOAD_MODELS = {
    "RankedCaseload": models.RankedCaseload,   # GET /caseload
    "ResidentDetail": models.ResidentDetail,   # GET /residents/{id}
    "IncidentEvent": models.IncidentEvent,     # SSE /incidents/stream
}

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contract.schema.json"


def contract_schema() -> dict:
    return {
        "$comment": "GENERATED from app/models.py by `python -m app.contract`. "
                    "Do not hand-edit. Mirrors triage-dashboard/lib/types.ts.",
        "payloads": {
            name: model.model_json_schema(by_alias=True)
            for name, model in PAYLOAD_MODELS.items()
        },
    }


def write_schema() -> Path:
    SCHEMA_PATH.write_text(
        json.dumps(contract_schema(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return SCHEMA_PATH


if __name__ == "__main__":
    print("wrote", write_schema())
