# Third-Party Dependencies & Sources Disclosure

All libraries, models, and tools utilized in the IncuBrix Video Editing Engine have been verified for **commercial usability** in compliance with Rule 2 of the IncuBrix Engineering Assessment.

---

## 1. Backend Libraries (Python)

| Library / Tool | Version | License | Commercial Use | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI** | `0.115.0` | MIT | Permitted | High-performance asynchronous REST API framework. |
| **Pydantic** | `2.9.0` | MIT | Permitted | Data validation, structured models, and settings management. |
| **pydantic-settings** | `2.5.0` | MIT | Permitted | Environment variable parsing and startup validation. |
| **Uvicorn** | `0.30.0` | BSD-3-Clause | Permitted | ASGI production web server. |
| **Httpx** | `0.27.0` | BSD-3-Clause | Permitted | Asynchronous HTTP client for webhooks and downloads. |
| **PyYAML** | `6.0.2` | MIT | Permitted | Scripted session file parsing for CLI runner. |
| **Boto3** | `1.35.0` | Apache 2.0 | Permitted | S3 and MinIO object storage client. |
| **Structlog** | `24.4.0` | MIT / Apache 2.0 | Permitted | Structured JSON logging. |
| **Aiofiles** | `24.1.0` | Apache 2.0 | Permitted | Asynchronous file I/O operations. |
| **Pytest** | `8.3.0` | MIT | Permitted | Automated test suite execution. |

---

## 2. Frontend Libraries (Node.js)

| Library | Version | License | Commercial Use | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **React** | `18.3.0` | MIT | Permitted | UI component framework. |
| **React DOM** | `18.3.0` | MIT | Permitted | DOM rendering engine for React. |
| **Axios** | `1.7.0` | MIT | Permitted | HTTP client for backend API communication. |
| **Vite** | `5.4.0` | MIT | Permitted | Frontend bundler and development server. |

---

## 3. Media Processing & Infrastructure

| Tool | Version | License | Commercial Use | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **FFmpeg** | `6.1+` | LGPL 2.1+ | Permitted | Media trimming, concatenation, retiming, audio filtering, and rendering. |
| **FFprobe** | `6.1+` | LGPL 2.1+ | Permitted | Stream inspection, duration extraction, and format validation. |
| **MinIO** | `RELEASE.2024` | AGPLv3 (Local Container Only) | Permitted in Container | Local S3-compatible object storage container. Shipped service uses standard S3 SDK. |
| **Docker** | `24+` | Apache 2.0 | Permitted | Service containerization. |

---

## 4. AI Models & Providers

| Provider / Model | Version / Type | License / Terms | Commercial Use | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **IncuBrix Rule Engine** | `1.0.0` (In-house) | Proprietary / IncuBrix | Permitted | Deterministic offline instruction parsing and test execution. |
| **OpenAI Whisper** | `whisper-1` / `faster-whisper` | MIT / Commercial API | Permitted | Speech-to-text with word-level timestamps. |
| **OpenAI GPT-4o-mini** | `gpt-4o-mini-2024-07-18` | Commercial API | Permitted | Optional natural language instruction parsing adapter. |

---

## 5. Media & Datasets

- **Test Video Fixtures**: Synthetic video created using FFmpeg color generators and synthetic sine wave tones, completely free of copyright or personal voice/likeness restrictions.
- **Transcript Fixtures**: Synthetically authored interview dialogue designed to test all 14 editing operations and edge cases.
