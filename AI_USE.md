# AI Assistance & Tools Disclosure

In accordance with Rule 1 of the IncuBrix Engineering Assessment (*"Disclose everything: List every AI coding tool used and explain what it was used for in AI_USE.md"*), this document provides a complete and transparent accounting of all AI tools utilized during the design, implementation, and verification of this system.

---

## 1. AI Coding Assistants Employed

| Tool / Model | Developer | Primary Areas of Contribution |
| :--- | :--- | :--- |
| **Claude Opus 4.6 (Thinking)** | Anthropic | Architecture brainstorming, Pydantic data modeling, mathematical coordinate mapping design, and initial code scaffolding. |
| **Gemini 3.8 Flash (High)** | Google DeepMind | Fast multi-file implementation, test suite authoring, session test runner integration, and comprehensive documentation generation. |

---

## 2. Scope & Nature of AI Contributions

1. **Architecture & Schema Design**:
   - Assisting with the formulation of the pure-functional `TimelineEngine` model.
   - Drafting the JSON Schema for the `Timeline` data contract and defining half-open interval boundaries $[s, e)$.

2. **Core Implementation**:
   - Generating boilerplate for FastAPI routes, OpenAPI 3.1 definitions, and Pydantic v2 schemas.
   - Authoring the FFmpeg `filter_complex` filter chain assembly logic (including `atempo` chaining, `drawtext` caption styling, and sine wave bleep tone generation).
   - Implementing rule-based regex patterns for the offline deterministic `MockLLMAdapter`.

3. **Testing & QA**:
   - Constructing 40+ automated Pytest unit scenarios covering interval math, segment splitting, undo/redo stacks, and anchor shifts.
   - Authoring 20 scripted session YAML files covering the 8-step worked example and 12 hard cases.

4. **Documentation**:
   - Formatting `README.md`, `REPORT.md`, `openapi.yaml`, and `docs/timeline-anchors.md`.

---

## 3. Human Oversight & Code Understanding

- **Full Verification**: Every generated module has been reviewed, type-checked, and verified via executable tests.
- **Architectural Ownership**: The core principle—that edits belong to content rather than clock positions—and the resulting coordinate transformation algorithms were architected to meet IncuBrix requirements and can be fully defended and explained during the live technical interview.
- **No Unchecked Code**: No code was accepted without local test execution and validation against the official assessment criteria.
