# PROJECT 1: "Clause" — A Contract & Policy Intelligence System with Citations and a Confidence Budget

## Problem statement.
Teams (legal ops, procurement, compliance) need to ask natural-language questions across a corpus of contracts, policies, and regulations and get answers that are grounded, cited to the exact clause, and honest about uncertainty — because a confidently wrong answer about an indemnification clause is worse than no answer. Generic RAG demos return a paragraph and a vibe. This system returns an answer, the exact source clauses, a faithfulness score, and refuses (or escalates) when grounding is weak.

## Why this isn't generic / why a startup HR won't neglect it.
It's not "chat with a PDF." It's a domain where being wrong has consequences, so it forces you to build the production rigor that's actually the job: clause-level citations, an eval harness that measures faithfulness, PII/sensitive-data handling, access-control-aware retrieval, and explicit uncertainty communication. RAG is also the single most hireable pattern: the most effective project for immediate hiring is a Retrieval Augmented Generation System because it solves common business problems by grounding language models in specific enterprise data for accuracy. You're doing the hireable pattern with the rigor most candidates skip.

## Architecture overview.

```text
┌─────────────────────────────────────┐
User ──HTTPS──
│ FastAPI gateway (async)
│ • authn/authz 
│ • input validation
└───────────────┬────────────────────┘
                │
┌───────────────┼──────────────────────┐
▼               ▼                      ▼
┌──────────────┐              ┌────────────────┐
│ Query router │              │ Semantic cache │
│ (cheap model)│              │ (Redis)        │
└──────┬───────┘              └────────────────┘
       │
┌──────────────┐
│ PII redactor │
│ (pre-LLM)    │
└──────────────┘
       │
       ▼
┌───────────────────────────────────────────────┐
│ Hybrid Retriever                              │
│ • BM25 (keyword) • dense (Qdrant)    │
│ • metadata filter (access scope, doc type)    │
│ • cross-encoder re-ranker                     │
└──────────────────┬────────────────────────────┘
                   ▼
┌───────────────────────────────────────────────┐
│ Grounded Generator                            │
│ • clause-level citation enforcement           │
│ • structured output (answer + citations +     │
│   confidence) via Pydantic                    │
│ • abstain/escalate if faithfulness < threshold│
└──────────────────┬────────────────────────────┘
                   ▼
┌───────────────────────────────────────────────┐
│ Eval + Observability (always-on)              │
│ • Ragas faithfulness/relevance on sample      │
│ • LangSmith trace of every step               │
│ • cost + latency per query logged             │
└───────────────────────────────────────────────┘

```

CI/CD: GitHub Actions → tests + eval-gate → Docker → PaaS (live demo)

Data: ingestion pipeline (parse → clause-aware chunk → embed → index)

## Component breakdown.

Ingestion pipeline — document parsing, clause-aware chunking (not blind 512-token splits — split on legal/policy structure), embedding with a selected + evaluated model, indexing into  Qdrant.
Hybrid retriever — BM25 + dense + RRF fusion, metadata pre-filtering for access scope, cross-encoder reranking with a latency budget.
Grounded generator — structured output (answer, citations[], confidence, abstained: bool); a self-check pass that verifies each claim maps to a retrieved clause.
Confidence budget — if faithfulness or retrieval score is below threshold, the system abstains and says so rather than guessing. This is your "communicating uncertainty" story made concrete.
Eval harness — a golden dataset of Q→expected-grounding pairs; Ragas metrics; CI fails if faithfulness regresses.
Guardrail layer — injection scanning on input, PII redaction before LLM + before logs, output filtering.
Cost/latency layer — semantic cache, query router (route trivial queries to a cheap model), per-query token + cost accounting surfaced in the UI.
Technologies.

Python/async, FastAPI, pgvector + Qdrant, Redis, an embedding model + cross-encoder reranker, Anthropic/OpenAI SDK, Ragas, LangSmith, Docker, GitHub Actions, a PaaS for the live demo.

(LangGraph not required here — keep Project 1 framework-light to prove you understand the primitives; that's a deliberate talking point.)

### Advanced features beyond tutorial level.

Clause-level citation enforcement with self-verification; abstention/escalation on low confidence; hybrid + rerank (most demos do pure-vector); access-control-aware retrieval; semantic caching; model routing for cost; a real eval suite gating CI.

### Reliability considerations.

Timeouts + exponential-backoff retries on every external call; circuit breaker around the LLM provider with a degraded fallback (return retrieved clauses without generation if the model is down — still useful); graceful "I can't answer confidently" path.

### Security considerations.

Input validation + prompt-injection scanning; PII detection and redaction pre-LLM and pre-log; metadata-enforced permission boundaries so users only retrieve documents in their scope; secrets via environment/secret manager, never in code. This directly answers understanding of data privacy and handling of sensitive data (PII/PHI).

### Evaluation methodology.

Golden dataset of realistic queries with known correct grounding; Ragas faithfulness/answer-relevance/context-relevance; LLM-as-judge for answer quality with identity-bias mitigation (use a different model family as judge than as generator); regression gate in CI; a small held-out adversarial set (injection attempts, out-of-corpus questions to test abstention).

### Observability strategy.

LangSmith trace of retrieve→rerank→generate→verify for every request; structured logs with a request ID; per-query metrics: retrieval score, faithfulness, latency breakdown (retrieval vs generation), tokens, cost. A simple /metrics dashboard or a Grafana-style view is a strong bonus.

### Deployment architecture.

Dockerized service + Postgres/pgvector + Redis via Docker Compose locally; GitHub Actions pipeline (lint → test → eval-gate → build image → deploy); hosted on Railway/Render/Fly with a public demo URL and a seeded demo corpus (use public contracts/policies so anyone can try it in 30 seconds). The eval-gate-in-CI is the detail that makes a hiring manager stop scrolling.



=======================================================================================================================
                            LOCAL DEVELOPMENT PIPELINE (WITH LIBRARY ECOSYSTEMS)
=======================================================================================================================

 ➊ DATA INGESTION
 ────────────────
   [ BROWSER CLIENT ] 
          │
          │  1. Request Upload URL (GET /get-upload-url?filename=book.pdf)
          ▼
   [ FastAPI APPLICATION ] (Port 8000)
          │  
          │  ⚡ Uses library: `boto3` (AWS SDK for Python)
          │  2. Calls: s3_client.generate_presigned_url('put_object', ...)
          │  
          ▼
   [ BROWSER CLIENT ]
          │
          │  3. Receives cryptographic Pre-signed URL string
          │  4. Runs Frontend code: `fetch(presigned_url, { method: 'PUT', body: fileFile })`
          ▼
 ➋ LOCAL STORAGE ENGINE
 ──────────────────────
   ┌────────────────────────────────────────────────────────┐
   │ MinIO CONTAINER (Port 9000 API / Port 9001 Console)    │ ◄── Managed via [ Docker Compose ]
   └────────────────────────────────────────────────────────┘
          │
          │  5. File upload completes successfully
          │  6. Fires a Webhook Bucket Notification instantly to FastAPI
          ▼
 ➌ TASKS BUFFERING & QUEUEING
 ─────────────────────────────
   [ FastAPI APPLICATION ] (Port 8000 Webhook Router)
          │
          │  ⚡ Uses framework: `Celery` (Distributed Task Queue)
          │  7. Offloads heavy job: process_pdf_task.delay(bucket, file_key)
          ▼
   ┌────────────────────────────────────────────────────────┐
   │ REDIS CONTAINER (Port 6379 Broker)                     │ ◄── Acts as the message ticker board
   └────────────────────────────────────────────────────────┘
          │
          │  8. Holds message ticket until background worker grabs it
          ▼
 ➍ BACKGROUND WORKER PROCESSING
 ──────────────────────────────
   [ CELERY WORKER PROCESS ] (Running standalone in a terminal window)
          │
          │  9. Pulls message ticket out of Redis queue
          │
          │  ⚡ Uses storage client: `boto3`
          │ 10. Sends HTTP Range Request header: "Range: bytes=0-4096"
          ▼
   [ MinIO CONTAINER ] (Port 9000)
          │
          │ 11. Returns HTTP 206 Partial Content (Only header metadata)
          ▼
   [ CELERY WORKER RAM BUFFER ]
          │
          │  ⚡ Uses standard python utility: `io.BytesIO`
          │ 12. Keeps file stream open inside computer memory (RAM)
          │ 13. Calculates target page byte offsets (e.g., Page 5 starts at byte 250,000)
          │ 14. Streams only page 5 slice over the network into RAM buffer
          ▼
 ➎ PARSING & TEXT CHUNKING ENGINE
 ────────────────────────────────
   [ TEXT EXTRACTION LAYER ]
          │
          │  ⚡ Uses parser library: `unstructured`
          │ 15. Extracts raw, unformatted clean text string from the RAM byte buffer
          ▼
currently till this point only

