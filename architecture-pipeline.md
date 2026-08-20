# System & Pipeline Architecture

This diagram shows how a single Compliance Card generation request flows through the application code, from raw JSON upload to stored, exportable output.

```mermaid
flowchart TD
    A["Input Artifacts:<br/>agent_config.json, tool_manifest.json, run_trace.json"] --> B["FastAPI Web Gateway<br/>(main.py)"]
    B --> C["Pydantic v2 Schema Validation<br/>(schema.py)"]

    C --> D["Deterministic Fact Extractor<br/>(parsers.py)"]
    D --> E["Regulation Mapping Engine<br/>(regulation_mapper.py)"]
    D --> F["Groq LLM Narrative Synthesizer<br/>(llm_extractor.py)"]

    E --> G["Compliance Card Orchestrator<br/>(generator.py)"]
    F --> G
    G --> H["Fact Checker &<br/>Anti-Hallucination Guard"]
    H --> I["Completeness Checker Engine<br/>(completeness.py)"]
    I --> J["Quantifiable Scoring Engine<br/>(scoring.py)"]

    J --> K["SQLAlchemy ORM<br/>Neon Cloud Postgres DB<br/>(crud.py / database.py)"]
    K --> L["Exporters:<br/>Structured JSON & Styled HTML Document<br/>(document.py)"]
    K --> M["AI Regulatory Auditor Reviewer<br/>(llm_extractor.py)"]
    K --> N["Card Patching & Version Manager<br/>(crud.py)"]
    N --> O["Version Diff Engine &<br/>Regulatory Impact Flagging"]
```

## Stage Summary

| Stage | Module | What Happens |
| :--- | :--- | :--- |
| Ingestion | `main.py`, `schema.py` | Uploads validated against Pydantic v2 schemas |
| Fact Extraction | `parsers.py` | Ground-truth tool permissions, PII sensitivity, decision authority, oversight triggers pulled directly from JSON |
| Regulation Mapping | `regulation_mapper.py` | Extracted facts mapped to EU AI Act, NIST AI RMF, ISO 42001 clauses |
| Narrative Synthesis | `llm_extractor.py` | Groq LLaMA 3.3 70B generates purpose/limitations text |
| Verification | Fact Checker Guard, `completeness.py` | LLM output checked against deterministic facts; missing/placeholder fields flagged |
| Scoring | `scoring.py` | 4-pillar weighted score (0–100), grade, risk badge |
| Persistence | `crud.py`, `database.py` | Immutable version saved to Neon Postgres |
| Export & Audit | `document.py`, `llm_extractor.py` | JSON/HTML export; AI Regulatory Auditor review |
| Versioning | `crud.py` | PATCH creates new immutable version; diff engine flags regulatory re-assessment |
