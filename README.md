# IncuBrix Prompt-Based Video Editing Engine (PS2)

A deterministic, content-anchored video editing engine that turns natural language instructions—such as *"cut out the ums"*, *"remove the part about pricing"*, and *"add a caption on the intro"*—into exact, reversible edits on a video while preserving audio/video synchronization and content attachment.

Built for the **IncuBrix Engineering Assessment 2**.

---

## 1. System Architecture

The IncuBrix engine strictly enforces the principle: **Edits belong to content, not clock positions.**

```
+-----------------------------------------------------------------------------------+
|                                 IncuBrix Engine                                   |
|                                                                                   |
|  [User Prompt] ---> [LLM Parser Adapter] ---> [Structured Operation]              |
|                             |                           |                         |
|                      (Mock or OpenAI)                   v                         |
|                                            [Deterministic Validation]             |
|                                                         |                         |
|                                                         v                         |
|                                              [Timeline State Machine]             |
|                                              - Immutable Source Media             |
|                                              - Half-Open Segments [s, e)          |
|                                              - Source-Time Content Anchors        |
|                                              - Linear Undo/Redo/Restore Stack     |
|                                                         |                         |
|                                                         v                         |
|                                             [Canonical Hasher (SHA-256)]          |
|                                                         |                         |
|  [Render Trigger] ------------------------------------->+                         |
|                                                         v                         |
|                                              [FFmpeg Filter Graph]                |
|                                              - atempo & setpts Speed Chains       |
|                                              - Frame-Accurate Cut Concatenation   |
|                                              - Sine Wave Bleep / Audio Mutes      |
|                                              - Styled Drawtext Captions           |
|                                              - Dynamic Ducked Background Music    |
|                                                         |                         |
|                                                         v                         |
|                                              [Post-Render Validation]             |
|                                              - Duration Check (<= 1 frame)        |
|                                              - Audio/Video Sync Verification      |
+-----------------------------------------------------------------------------------+
```

---

## 2. Technology Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, Uvicorn, Structlog
- **Media Engine**: FFmpeg (libx264, aac, filter_complex) & FFprobe
- **Storage**: Local filesystem & MinIO (S3-compatible)
- **Frontend**: React 18, Vite, Axios, HTML5 Video
- **Containerization**: Docker & Docker Compose
- **Interoperability**: OpenAPI 3.1, OpenTimelineIO-ready

---

## 3. Quick Start (Fewer Than 10 Commands)

### Option A: Running with Docker Compose (Recommended)

```bash
git clone <repository_url> && cd Incrubix
cp .env.example .env
docker compose up -d
# Frontend is live at http://localhost:3000
# API and Swagger Docs live at http://localhost:8000/docs
```

### Option B: Local Native Run (Offline / No Docker)

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd ../frontend && npm install && npm run dev
```

---

## 4. Running Tests

The test suite runs entirely **without paid API keys** or external internet dependencies using the built-in deterministic mock adapters:

```bash
# Run all unit, integration, determinism, and e2e tests:
cd backend
python -m pytest tests/ -v
```

---

## 5. Running the Batch Session Runner CLI

The CLI executes scripted session YAML files against the running engine (or directly in-process) and generates full evidence packs including `results.json`, `timeline.json`, and `manifest.json`.

```bash
# Run a single session:
python -m cli.runner sessions/session_08_worked_example.yaml --output ./results/

# Run the complete test suite of 20 scripted sessions:
python -m cli.runner sessions/ --output ./results/
```

---

## 6. Supported Editing Operations

Every accepted instruction triggers a deterministic timeline transformation:

1. **Cut a Range**: Cuts interval $[s, e)$ in source time or current timeline time.
2. **Keep Only a Range**: Retains interval $[s, e)$ and removes content outside it.
3. **Reorder Sections**: Permutes segment order while semantic anchors stay attached to their words.
4. **Change Playback Speed**: Modifies speed ($0.25\times$ to $10.0\times$), scaling audio via chained `atempo` filters.
5. **Mute Words**: Identifies target words and zeros audio volume during their intervals.
6. **Bleep Words**: Mutes spoken audio and injects a 1000 Hz sine wave tone during target words.
7. **Add Captions**: Attaches text overlays to semantic word timestamps rather than clock positions.
8. **Auto Captions**: Automatically generates word-level caption anchors across all active segments.
9. **Remove Filler Words**: Selectively cuts filler words (*um*, *uh*, and contextual *like*) based on transcript tags.
10. **Remove Silences**: Cuts dead air pauses longer than a threshold (default 2.0s) while preserving 0.3s speech padding.
11. **Background Music with Ducking**: Mixes music track and dynamically ducks audio levels when speech is active.
12. **Undo**: Reverses the previous edit transaction.
13. **Redo**: Reapplies the most recently undone edit.
14. **Restore Specific Edit**: Restores a specific prior edit or historical state non-destructively.

---

## 7. Required Three-Way Instruction Status

Every instruction receives exactly one of three statuses:

- `applied`: Operation was validated and successfully committed to the timeline.
- `needs_clarification`: Instruction was ambiguous or destructive; prompts user with options without altering the timeline.
- `rejected`: Instruction violates physical constraints (e.g., cutting the entire video, invalid timestamps).

---

## 8. Error Codes Specification

Errors strictly follow the official JSON contract:
`{"error": {"code": "UPPER_SNAKE_CASE", "message": "...", "retryable": false, "details": {}}}`

| Error Code | HTTP Status | Retryable | Description |
| :--- | :--- | :--- | :--- |
| `INVALID_VIDEO` | 400 | False | Corrupt video or unsupported format. |
| `VIDEO_NOT_FOUND` | 404 | False | Requested video asset does not exist. |
| `PROJECT_NOT_FOUND`| 404 | False | Project ID does not exist in data store. |
| `TIMELINE_ERROR` | 400 | False | Segment violation (e.g. attempt to cut entire video). |
| `INSTRUCTION_REJECTED` | 400 | False | Instruction impossible or violates policy. |
| `RENDER_FAILED` | 500 | False | FFmpeg process failed during compilation. |
| `STORAGE_ERROR` | 500 | True | Read or write failure in storage backend. |
| `JOB_NOT_FOUND` | 404 | False | Background job ID not found. |
| `IDEMPOTENCY_CONFLICT` | 409 | False | Concurrent or conflicting payload with same key. |
| `INVALID_REQUEST` | 400 | False | Schema validation error. |
| `INTERNAL_ERROR` | 500 | False | Unhandled server exception. |

---

## 9. Integration Standard Compliance Checklist

| # | Standard | Implementation Evidence |
|---|----------|------------------------|
| 1 | **One-command start & test** | `docker compose up` starts stack; `python -m pytest tests/` runs all tests offline. |
| 2 | **Documented HTTP API** | `openapi.yaml` (OpenAPI 3.1.0) strictly matches `/api/v1/` routes. |
| 3 | **Background jobs** | Asynchronous jobs for renders & ingestion. Returns 202 + `job_id`, polled via `GET /api/v1/jobs/{id}`. |
| 4 | **Safe retries** | `Idempotency-Key` header enforced and cached on all POST endpoints. |
| 5 | **Clear errors** | Structured JSON error responses with `UPPER_SNAKE_CASE` codes. |
| 6 | **Configuration** | All paths, models, and limits driven via `.env` (validated by Pydantic Settings). |
| 7 | **Files in, files out** | Uploads and URL ingestion; download URLs for videos and rendered outputs via MinIO/local storage. |
| 8 | **Logs and health** | Structured JSON logs with timestamps, levels, and `X-Correlation-Id`. `/health` and `/ready` probes. |
| 9 | **Output manifest** | Every rendered result produces `manifest.json` with models, timings, seed, and licensing. |
| 10 | **Batch runner** | `cli/runner.py` executes directory of scripted sessions and writes structured evidence. |

---

## 10. Known Limitations & Tradeoffs

1. **Extreme Speed Factors**: Factors above $8\times$ cause loss of speech intelligibility despite chained `atempo` filters; the system issues an explicit diagnostic warning.
2. **Variable Frame Rate (VFR)**: Handled gracefully via container-level timebase normalization, but exact single-frame accuracy is most dependable with Constant Frame Rate (CFR) sources.
3. **Overlapping Speech**: Single-channel transcription cannot cleanly separate overlapping speakers without diarization; the engine flags overlapping speaker tags as warnings.
