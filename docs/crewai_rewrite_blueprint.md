# CrewAI-first Rewrite Blueprint (New Repository)

Date: 2025-10-14

This document is a detailed blueprint to build a new CrewAI-first application from scratch (greenfield). No code will be reused from the current app—only domain knowledge. It defines a clean multi‑agent architecture, shared tools, and unified short/long‑term memory with actionable instructions to implement the system end‑to‑end.

---

## Goals and principles

- CrewAI-first: model the product as cooperating agents with clear roles and shared memory.
- Prefer built-in CrewAI capabilities (Agent, Crew, Tool, Memory/STM/LTM) over custom orchestration wherever possible.
- Contracts over heuristics: JSON contracts between agents and tools, versioned and testable.
- Single source of truth: one memory layer with short-term (conversation) and long-term (vector + SQL) views.
- Safety and approvals: side-effecting tools require concise, human confirmation.
- Observability: structured tracing for every plan, tool, and write. PII-safe by default.
- Windows-friendly DX: one-liner PowerShell setup and run targets.

---

## High-level architecture

Crews (domains) and their agents:

- Capture Crew (text/voice → actions/notes)
  - CrewAI: Define a `Crew` composed of multiple `Agent`s with shared memory.
  - OrchestratorAgent (CrewAI Agent): routes messages, reads/writes STM.
  - CapturePlannerAgent (CrewAI Agent): produces Plan JSON (intent, entities, tool candidates).
  - ClarifierAgent (CrewAI Agent): asks only for missing required fields.
  - ToolCallerAgent (CrewAI Agent): renders final ToolCall, handles approvals, executes Tools.

- Retrieval Crew (questions → grounded answers)
  - CrewAI: `Crew` with Agents QueryPlanner → Retriever → Composer (answers + citations).

- Diary Crew (daily synthesis)
  - CrewAI: `Crew` with Agents DiaryPlanner → DiaryWriter → DiaryPersist (0–1 clarifier).

- Tasks & Lists Crew (NL to tasks/lists/reminders)
  - CrewAI: `Crew` with Agents TaskExtractor → ConfidenceGate → Scheduler.

- Integrations Crews (phased)
  - Google Crew: SyncAgent (Calendar/Tasks) + WriteAgent (approval gated).
  - News Crew: DigestAgent + PostAgent (LinkedIn) with RepostGuard.
  - Actions Crew: generic orchestrator for side‑effecting operations (approve → execute → audit).

Shared libraries:
- Memory Service (CrewAI-backed): use CrewAI STM/LTM primitives when possible.
  - STM: CrewAI Conversation/Shared Memory across Agents in the Crew.
  - LTM: CrewAI VectorStore-backed memory (e.g., Chroma/FAISS) exposed via a thin facade.
- Tool Registry: idempotent, auditable tool wrappers.
- Contracts: pydantic schemas and JSON Schema for Plans, ToolCalls, MemoryItem, Task, List, Reminder.
- Telemetry: tracer/logger with correlation IDs.

---

## Memory model

- Short-term memory (STM)
  - CrewAI: use CrewAI Conversation/ShortTerm memory bound to the Crew/Agents and keyed per chat/session.
  - Bounded window, role-tagged messages, TTL.
  - Persist STM snapshots to SQLite for durability if CrewAI memory does not persist by default.
  - Accessible to any agent via Memory API (get_history(chat_id), append(role, text), truncate(K)).

- Long-term memory (LTM)
  - CrewAI: use CrewAI Long-Term Memory integration with a vector backend (Chroma/FAISS), plus SQL metadata for structure.
  - Normalized entity: MemoryItem { id, source, created_at, title, content, tags[], people[], temporal fields, attachments, section }.
  - Write-path through ToolCaller (after approval). Index and persist once.

- CrewAI linkages
  - Use CrewAI’s memory injection to give Agents access to STM/LTM; wrap with a Memory API for domain conveniences.
  - Retrieval Crew composes prompts strictly from LTM items (with citations). Zero‑evidence policy for personal facts.

---

## Contracts (pydantic + JSON Schema)

- Plan
  - intent: enum [task.create, task.complete, reminder.schedule, list.create, list.delete, list.add, list.remove, list.item.complete, memory.note, diary.entry, command.query, unknown]
  - entities: { list?, items[], title?, due_at?, happened_at?, person_refs[], place_refs[] }
  - followups: [{ ask, field }]
  - actions: [{ tool, params }]
  - safety: { blocked: bool, reason?: str }

- ToolCall
  - tool: string (registry key)
  - params: object (validated per-tool schema)
  - idempotency_key?: string
  - CrewAI: not to be confused with `crewai.Task`. This is a domain call envelope for Tools.

- MemoryItem (long-term)
  - id, source, created_at, title, content, tags[], people[], event_start_at?, event_end_at?, timezone?, date_bucket?, media_type?, media_path?, location?, section?, external_id?, status?, due_at?, attendees[]

- Task / List / Reminder
  - Task { id, title, status, due_at?, list, external_id? }
  - List { name, type }
  - Reminder { id, task_id?, trigger_at, message, status, chat_id }

All contracts versioned under `contracts/` with JSON Schema for runtime validation (and tests).

---

## Tools (shared registry)

- ListTool: create/delete/add/remove/item.complete
- TaskTool: create/complete
- ReminderTool: schedule/cancel (if needed)
- MemoryNoteTool: create note (writes MemoryItem with section=event/diary)
- StorageTool: filesystem paths, hashed storage for attachments
- GeoTool: reverse geocoding + cache
- TemporalTool: EU/Madrid↔UTC normalization, date_bucket
- PeopleTool: canonicalize @mentions
- IdempotencyTool: dedupe by hash of action

Design:
- Each tool declares `schema` and `execute(context, params)` and returns `{ result, target: {type,key} }`.
- CrewAI: implement Tools as CrewAI Tool objects (e.g., subclassing `BaseTool` or the framework’s tool pattern) and attach them to the relevant Agents.
- Idempotent writes (log and skip duplicates).
- Registry enforces confirmation for side effects (unless explicitly marked safe).

---

## Observability

- Trace JSONL (app-level): `data/trace.jsonl` per environment (prod/test/dev)
  - Events: plan.start/end, clarifier.ask, tool.execute.start/end, memory.write, retrieval.*, diary.*
  - Fields: ts, env, chat_id, user_id, event, seq, dur_ms, ok, error, preview
- Metrics: per-tool counters, plan followups count, confirmation rate, retrieval evidence counts
- Log scrubber: redact PII on outbound logs (opt-in raw capture for dev only)

---

## Configuration (env)

Core:
- APP_ENV=dev|test|prod
- TELEGRAM_BOT_TOKEN=...
- VECTOR_BACKEND=chroma|hybrid|stub
- VECTOR_STORE_PATH=data/chroma
- SQL_DB_PATH=data/app.sqlite (STM + metadata)
- DIARY_HOUR=23
- ZERO_EVIDENCE_POLICY=strict|allow
- MAX_CLARIFY_QUESTIONS=3
- APPROVAL_REQUIRED=1
- TRACE_LEVEL=info|debug

LLM:
- LLM_BACKEND=ollama|openrouter|azure-openai
- OLLAMA_MODEL=...
- OPENROUTER_API_KEY=...

---

## Recommended repository structure

```
new-repo/
  pyproject.toml
  README.md
  .env.example
  src/
    app/
      main.py                 # entry (Telegram adapter, HTTP if needed)
      config.py               # env loading
      tracing.py              # tracer/logger
      memory/                 # STM+LTM abstraction
        __init__.py
        short_term.py
        long_term.py
        schemas.py            # MemoryItem
      contracts/
        __init__.py
        plan.py
        toolcall.py
        schemas/              # JSON Schemas
      tools/
        __init__.py
        registry.py
        list_tool.py
        task_tool.py
        reminder_tool.py
        memory_note_tool.py
        storage_tool.py
        temporal_tool.py
        geo_tool.py
        people_tool.py
      crews/
        capture/
          orchestrator.py
          planner.py
          clarifier.py
          tool_caller.py
        retrieval/
          planner.py
          retriever.py
          composer.py
        diary/
          planner.py
          writer.py
          persist.py
        integrations/
          google/
            sync.py
            write.py
          news/
            digest.py
            post.py
        actions/
          orchestrator.py
      adapters/
        telegram.py
        http.py                # optional HTTP ingress for web clients
      utils/
        idempotency.py
        time.py
  tests/
    unit/
    integration/
    golden/
  docs/
    architecture.md
    crews.md
    contracts.md
    runbook.md
  scripts/
    dev_seed.py
```

---

## Greenfield implementation plan

Phased delivery with working software at every step. All code, contracts, and prompts live in this new repository. No connectors to the previous app.

Phase 0 — Project scaffold (Done when: tests run, linting passes)
- Repo bootstrap: pyproject, src layout, tests, pre-commit, CI pipeline.
- Config loader and typed settings.
- Tracer/logger with JSONL sink per environment.

Phase 1 — Memory foundation (STM + LTM)
- CrewAI: Configure CrewAI STM for conversations (per chat/session) and LTM for retrieval.
- Implement MemoryItem schema and configure CrewAI’s vector memory (Chroma/FAISS) + SQL metadata service.
- Provide a unified Memory API consumed by agents (wrap CrewAI memory, avoid raw store access).

Phase 2 — Tool Registry and core tools
- CrewAI: Define Tools using CrewAI tool constructs and attach to Agents.
- Implement registry with per-tool JSON Schema validation and idempotency keys.
- Tools: ListTool (create/delete/add/remove/item.complete), TaskTool (create/complete), ReminderTool (schedule), MemoryNoteTool.
- Add TemporalTool/PeopleTool/StorageTool for normalization and attachments.

Phase 3 — Capture Crew (MVP)
- CrewAI: Implement a Crew with Agents (Planner, Clarifier, ToolCaller) and shared STM.
- Enforce: single action per turn, JSON-only plans, and confirmations.
- E2E tests for note capture and simple list/task flows.

Phase 4 — Retrieval Crew
- CrewAI: Implement QueryPlanner → Retriever → Composer Agents using CrewAI; plug LTM for context.
- Zero-evidence policy; golden tests for answers.

Phase 5 — Diary Crew
- CrewAI: Implement Agents for DayWindow → DiaryWriter → Persist; share LTM across days.
- Optional clarifier (max 1 question).

Phase 6 — Integrations and adapters
- Telegram adapter (productionized), optional HTTP ingress for web.
- CrewAI: Expose a thin adapter that forwards messages into the Capture Crew; reuse CrewAI’s conversation memory per chat.
- Feature flags and rate limits.

Acceptance criteria per phase
- Unit and integration tests green; coverage ≥80% for units.
- Trace events for plan/tool/memory/retrieval/diary present with correlation IDs.
- Performance baselines documented (retrieval p95 < 300ms on dev machine with stub store).

---

## Testing strategy

- Unit tests
  - Contracts: schema validate minimal and full examples (Plan, ToolCall, MemoryItem).
  - Tools: happy + edge (missing fields, idempotency).
  - Memory API: STM windowing, LTM index/save/load.

- Integration tests
  - Capture Crew E2E: ambiguous → clarifier → confirm → write.
  - Retrieval Crew: fact/day/generic with golden answers and citations.
  - Diary Crew: day synthesis fixture.

- Golden tests for prompts
  - Keep prompt templates under version control; snapshot expected model outputs for a tiny local model; allow small diffs.

- Performance & health
  - Index load/save time, retrieval latency percentiles, diary synthesis duration.

- Coverage target: 80% unit; integration suites in CI.

---

## CI/CD (GitHub Actions)

- Workflows
  - ci.yml: Python 3.11/3.12 matrix → ruff lint → black check → pytest -q
  - release.yml: tag push → build wheel/sdist → publish (optional)

- Pre-commit
  - ruff, black, end-of-file-fixer, trailing-whitespace.

- Artifacts
  - Upload coverage.xml, test reports (JUnit), and trace samples for failed runs.

---

## Runbook (Windows PowerShell)

Prereqs: Python 3.11+; ffmpeg if using audio; Chroma optional.

Setup venv and install:

```powershell
# From repo root
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .[dev]
# Optional: install chromadb for vector store
pip install chromadb
# Pre-commit hooks
pre-commit install
```

Environment and first run:

```powershell
# Copy and edit environment
Copy-Item .env.example .env
# Set your TELEGRAM_BOT_TOKEN and LLM settings in .env

# Run Telegram adapter (dev)
python -m app.main
```

Dev helpers:

```powershell
# Run unit tests
pytest -q
# Run a subset
pytest -q tests/integration/test_capture_e2e.py::test_note_happy
# Lint & format check
ruff check src tests
black --check src tests
```

---

## Prompts and guardrails (capture)

- CapturePlannerAgent: produces Plan JSON only (no prose). If insufficient fields, add followups.
- ClarifierAgent: asks a single, concrete question per turn; max MAX_CLARIFY_QUESTIONS.
- ToolCallerAgent: presents a one‑line confirmation (title/date/target). Executes only on explicit Sí/Yes.
- Diary/Retrieval: insist on citations; zero‑evidence → “No puedo encontrarlo en tus notas”.

---

## Risks and mitigations

- Prompt drift across agents
  - Golden tests; keep prompts minimal; version prompts.
- Tool idempotency & duplication
  - Hash inputs; log action_hash; guard writes.
- Memory fragmentation
  - Single Memory API and schemas; adapters only at the edges.
- Migration complexity
  - Shadow mode; per‑phase cutover with revert flag.
- Model variability
  - Prefer smaller, more predictable models for planners; composer can be larger.

---

## Milestones & acceptance

- M0: Repo skeleton + Memory API + Tool Registry (Done when: unit tests green; runbook works)
- M1: Capture Crew (memory.note) with approvals (E2E test green; writes under new source)
- M2: Lists/Tasks/Reminders tools (contracts + E2E tests; idempotency proven)
- M3: Retrieval Crew parity (answers with citations; golden tests pass)
- M4: Diary nightly (synthesis writes; smoke test)
- M5: Cutover + remove old runner (metrics steady for 7 days)

---

## Appendix: JSON Schema snippets (illustrative)

Plan (excerpt):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["intent"],
  "properties": {
    "intent": {
      "type": "string",
      "enum": ["task.create","task.complete","reminder.schedule","list.create","list.delete","list.add","list.remove","list.item.complete","memory.note","diary.entry","command.query","unknown"]
    },
    "entities": { "type": "object" },
    "followups": { "type": "array", "items": { "type": "object", "required": ["ask","field"] } },
    "actions": { "type": "array", "items": { "type": "object", "required": ["tool","params"] } }
  }
}
```

ToolCall (per‑tool schemas validated at runtime).

MemoryItem (align with current `MemoryItem` dataclass; extend if needed).

---

This blueprint is intended to be living documentation; update as crews and contracts evolve.
