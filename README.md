<img width="1536" height="1024" alt="Worksflow-3" src="https://github.com/user-attachments/assets/b70d5a9c-61f1-491f-963c-9a3095a5ace3" />

# Enterprise Knowledge-Aware LLM (EKLLM)

A self-hosted AI assistant that makes your entire organisation's engineering knowledge queryable — codebase, architecture decisions, past incidents, git history, and internal docs — all answered by a fine-tuned Llama 3 8B running locally.

---

## Why We Built This

Every engineering team carries invisible knowledge:

- Why was that database chosen 3 years ago?
- What caused last quarter's payment outage?
- Which services break if we change OrderService?
- What does this 5-year-old legacy module actually do?

This knowledge lives scattered across Confluence pages, Slack threads, closed Jira tickets, git commit messages, and the heads of engineers who may have left. New developers waste weeks onboarding. Senior engineers spend hours answering the same questions repeatedly. Post-incident investigations start from zero every time.

EKLLM solves this by ingesting all of that institutional knowledge, building a semantic + graph representation of it, and exposing it through a chat interface powered by a domain-adapted LLM — entirely on your own infrastructure with no data leaving your network.

---

## Main Goals

1. **Zero data egress** — everything runs locally: LLM inference, vector DB, graph DB, embeddings.
2. **Multi-source ingestion** — code repos, PDFs, Markdown docs, Jira/incident tickets, all become queryable.
3. **Hybrid retrieval** — vector similarity search (Qdrant) combined with graph traversal (Neo4j) for richer context.
4. **Specialized AI agents** — four domain-expert agents (code analysis, architecture, bug diagnosis, org memory) orchestrated by a LangGraph planner.
5. **Fine-tuning pipeline** — QLoRA fine-tuning on Llama 3 8B using your organisation's own data to get domain-specific answers.
6. **Production-ready** — JWT auth, async workers, CI/CD, Prometheus/Grafana monitoring, Kubernetes manifests.

---

## How It Works — Step by Step

### 1. Data Ingestion

You feed the system your organisation's knowledge through two channels:

**Document upload** (PDF, Markdown, YAML, JSON, plain text):
1. File is received by the FastAPI endpoint and saved to disk.
2. A SHA-256 hash check prevents duplicate ingestion.
3. A Celery task is queued in Redis.
4. The worker parses the file using the appropriate parser (PDF → PyPDF2, Markdown, code files).
5. Content is chunked into overlapping segments.
6. Each chunk is embedded using `BAAI/bge-large-en-v1.5`.
7. Vectors are stored in Qdrant; metadata + document record in PostgreSQL.
8. spaCy + regex entity extraction identifies Services, Modules, APIs from the text.
9. Extracted entities and relationships are written to Neo4j.

**Git repository ingestion**:
- Clones the repo, walks code files and commit history.
- Same chunk → embed → store pipeline applies.
- Code entities are linked in the knowledge graph.

**Incident/Jira data**:
- Ingested via API; embedded and stored in a dedicated `incidents` Qdrant collection.
- Used exclusively by the Bug Intelligence Engine.

---

### 2. Knowledge Graph (Neo4j)

After ingestion, a graph is built of your entire software ecosystem:

**Node types:** `Service`, `Module`, `Class`, `Function`, `Developer`, `API`, `Incident`, `BugPattern`, `ArchDecision`, `Team`

**Relationship types:** `DEPENDS_ON`, `PUBLISHES`, `CONSUMES`, `CREATED_BY`, `AFFECTED_BY`, `DECIDED_BY`, `REPLACED_BY`, `REJECTED_ALTERNATIVE`

This graph powers:
- Dependency traversal (which services depend on what, up to 3–5 hops)
- Impact analysis (what breaks if I change this component)
- Incident history per service
- Architectural decision lineage

---

### 3. Query & Multi-Agent Orchestration

When a developer asks a question, a LangGraph state machine runs:

```
Query
  │
  ▼
Planner Node  ←── LLM decides which agents are needed
  │
  ├──► CodeAnalysis Agent    ←── Qdrant vector search, top 6 chunks
  ├──► Architecture Agent    ←── Qdrant + Neo4j graph context
  ├──► BugDiagnosis Agent    ←── incidents collection + root cause clustering
  └──► OrgMemory Agent       ←── arch_decisions collection
         │
         ▼
   Synthesis Node  ←── LLM combines all agent outputs into one answer
         │
         ▼
   Validator Node  ←── assigns confidence score
         │
         ▼
   Response (answer + citations + graph_context + confidence)
```

Each agent runs in parallel after the planner decides which ones are needed. The synthesis node then uses the LLM to produce a single coherent answer citing all findings.

---

### 4. Hybrid Retrieval (RAG + Graph)

The `RAGQueryService` combines two retrieval signals:

- **Vector search** — embeds the query and finds the top-K semantically similar chunks from Qdrant.
- **Graph traversal** — if an entity name is hinted (e.g. "OrderService"), Neo4j is queried for 1-hop relationships to enrich context.

This means answers about a specific service include not just document snippets but also live relationship data (what it depends on, what incidents it had, etc.).

---

### 5. Bug Intelligence Engine

Paste an error log or describe a production incident. The engine:

1. Embeds the error description.
2. Searches the `incidents` Qdrant collection for the top 10 most similar past incidents.
3. Clusters root causes by weighted similarity score.
4. Returns the most probable root cause, confidence %, deduplicated recommended fixes, and links to the 3 most relevant past incidents.

---

### 6. Organizational Memory

Architectural decisions (ADRs), migration plans, and engineering conventions are stored with:
- Semantic vector in Qdrant (`arch_decisions` collection)
- Nodes + `REJECTED_ALTERNATIVE` edges in Neo4j

The OrgMemory Agent can answer "Why did we choose Kafka over RabbitMQ?" or "What was the rationale for migrating to microservices?" by retrieving the stored decision and its full context.

---

### 7. Fine-Tuning Pipeline (Optional)

To improve answer quality on your domain-specific terminology:

1. **Dataset Builder** — auto-generates instruction-tuning examples from your code chunks, incidents, and ADRs using prompt templates.
2. **Quality pipeline** — deduplicates examples, filters low-quality outputs.
3. **QLoRA fine-tuning** — trains Llama 3 8B with 4-bit quantization (fits on a single 24GB GPU) using PEFT/TRL.
4. The fine-tuned adapter is saved and can be loaded into vLLM.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM Inference | vLLM + Llama 3 8B Instruct |
| Embeddings | BAAI/bge-large-en-v1.5 (via sentence-transformers) |
| Vector DB | Qdrant |
| Graph DB | Neo4j 5 (Community) + APOC + GDS plugins |
| Relational DB | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| Async Workers | Celery 5 |
| Agent Framework | LangGraph + LangChain |
| Entity Extraction | spaCy (en_core_web_sm) |
| Backend | FastAPI + SQLAlchemy (async) + Alembic |
| Fine-tuning | PEFT QLoRA + TRL SFTTrainer + bitsandbytes |
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Graph Visualisation | react-force-graph-2d |
| Monitoring | Prometheus + Grafana |
| Container | Docker Compose / Kubernetes (Kustomize) |
| CI/CD | GitHub Actions |

---

## Project Structure

```
enterprise-knowledge-llm/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints: auth, ingest, query, graph
│   │   ├── core/            # config, security (JWT), logging, exceptions
│   │   ├── db/              # Qdrant, Neo4j, Redis, PostgreSQL clients
│   │   ├── middleware/      # audit logging middleware
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── repositories/    # data access layer
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── agents/      # LangGraph orchestrator + 4 specialist agents
│   │   │   ├── bug_intelligence/   # historical incident diagnosis engine
│   │   │   ├── ingestion/   # parse → chunk → embed pipeline
│   │   │   ├── knowledge_graph/    # Neo4j CRUD + graph queries
│   │   │   ├── org_memory/  # architectural decision store + retrieval
│   │   │   └── rag/         # embedder, vector store, hybrid query
│   │   └── workers/         # Celery app + async task definitions
│   └── tests/
├── frontend/
│   └── src/app/
│       ├── chat/            # main AI chat interface
│       ├── graph/           # interactive knowledge graph visualiser
│       ├── incidents/       # bug diagnosis UI
│       ├── ingest/          # document & git repo ingestion UI
│       └── memory/          # org memory browser
├── knowledge-graph/
│   ├── pipelines/           # entity_extractor.py (spaCy + regex)
│   ├── queries/             # reusable Cypher query helpers
│   └── schemas/             # neo4j_schema.cypher (constraints + indexes)
├── training/
│   ├── dataset_builder/     # auto-generate instruction-tuning examples
│   ├── finetuning/          # QLoRA train.py
│   ├── evaluation/          # ROUGE + custom evaluator
│   └── configs/             # qlora_llama3_8b.yaml
├── monitoring/
│   ├── prometheus/          # prometheus.yml scrape config
│   └── grafana/dashboards/  # pre-built backend dashboard
├── deployment/
│   └── kubernetes/          # Kustomize base + overlays
├── .github/workflows/ci.yml # test → lint → build → deploy pipeline
├── docker-compose.yml
└── .env.example
```

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- NVIDIA GPU with ≥ 16GB VRAM for vLLM (RTX 3090 / A10 / etc.)
- NVIDIA Container Toolkit installed
- HuggingFace account with access to `meta-llama/Meta-Llama-3-8B-Instruct`
- Git

> **No GPU?** You can still run everything except vLLM. Point `VLLM_BASE_URL` to any OpenAI-compatible API (OpenAI, Ollama, etc.) and the rest of the stack works unchanged.

---

## How to Run

### 1. Clone the repo

```bash
git clone https://github.com/your-org/enterprise-knowledge-llm.git
cd enterprise-knowledge-llm
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set:

```env
HF_TOKEN=hf_your_actual_token_here      # required to pull Llama 3
SECRET_KEY=your-random-secret-key       # used for JWT signing
LLM_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
```

All other defaults work out of the box for local development.

### 3. Start all services

```bash
docker compose up -d
```

This starts: PostgreSQL, Qdrant, Neo4j, Redis, vLLM, backend API, Celery worker, frontend, Prometheus, Grafana.

First run will download the Llama 3 model (~16GB) — this takes time depending on your connection.

### 4. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 5. (Optional) Bootstrap Neo4j schema

Open Neo4j Browser at `http://localhost:7474` (user: `neo4j`, password from `.env`) and run:

```
:source /knowledge-graph/schemas/neo4j_schema.cypher
```

Or copy-paste the contents of `knowledge-graph/schemas/neo4j_schema.cypher`.

### 6. Access the application

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |
| Qdrant dashboard | http://localhost:6333/dashboard |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin / admin) |

### 7. Register a user and start chatting

1. Go to `http://localhost:3000`
2. Register an account via the UI or `POST /api/v1/auth/register`
3. Log in to get a JWT token
4. Go to the **Ingest** page and upload a PDF or paste a git repo URL
5. Wait for the ingestion job to complete (check status via the API or Celery logs)
6. Go to **Chat** and ask questions about your ingested content

---

## Ingesting Your Own Data

### Upload a document

```bash
curl -X POST http://localhost:8000/api/v1/ingest/document \
  -H "Authorization: Bearer <your_token>" \
  -F "file=@/path/to/your/doc.pdf" \
  -F "source_type=pdf"
```

### Ingest a git repository

```bash
curl -X POST http://localhost:8000/api/v1/ingest/git \
  -H "Authorization: Bearer <your_token>" \
  -F "repo_url=https://github.com/your-org/your-repo" \
  -F "branch=main"
```

### Check ingestion job status

```bash
curl http://localhost:8000/api/v1/ingest/status/<job_id> \
  -H "Authorization: Bearer <your_token>"
```

---

## Running the Fine-Tuning Pipeline

Only needed if you want to adapt the LLM weights to your domain vocabulary.

### 1. Build the training dataset

```bash
cd training
pip install -r requirements.txt
python scripts/build_dataset.py
```

This generates `data/splits/train.jsonl`, `validation.jsonl`, `test.jsonl`.

### 2. Run QLoRA fine-tuning

```bash
python scripts/run_training.py --config configs/qlora_llama3_8b.yaml
```

Requires a GPU with ≥ 24GB VRAM. Training runs 3 epochs with bfloat16, gradient checkpointing, and paged AdamW.

The fine-tuned adapter is saved to `training/checkpoints/llama3-8b-ekllm/`.

---

## API Reference

All endpoints require `Authorization: Bearer <token>` except auth routes.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create a new user |
| POST | `/api/v1/auth/login` | Get JWT token |
| POST | `/api/v1/query/` | Ask a question (full agent pipeline) |
| POST | `/api/v1/query/diagnose` | Diagnose a bug/error |
| POST | `/api/v1/query/impact` | Component impact analysis |
| POST | `/api/v1/ingest/document` | Upload and ingest a document |
| POST | `/api/v1/ingest/git` | Clone and ingest a git repo |
| GET | `/api/v1/ingest/status/{job_id}` | Check ingestion job status |
| GET | `/api/v1/graph/dependencies/{service}` | Service dependency graph |
| GET | `/api/v1/graph/impact/{component}` | Impact analysis via graph |
| GET | `/api/v1/graph/incidents/{service}` | Incident history for a service |
| GET | `/api/v1/graph/visualize` | Full graph for visualisation |

Full interactive docs at `http://localhost:8000/docs`.

---

## Running Tests

```bash
docker compose exec backend pytest tests/ -v
```

Or locally:

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v --tb=short
```

---

## CI/CD Pipeline

GitHub Actions runs on every push to `main` or `develop`:

1. **test-backend** — spins up PostgreSQL + Redis, runs the full pytest suite
2. **lint** — runs `ruff check` on the backend
3. **build-and-push** — builds and pushes the Docker image to Docker Hub (main branch only)
4. **deploy** — applies Kubernetes manifests and rolls out a new deployment (main branch only)

Requires GitHub secrets: `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `KUBE_CONFIG`.

---

## Monitoring

Prometheus scrapes the FastAPI metrics endpoint (`/metrics`, exposed automatically). Grafana comes pre-configured with a backend dashboard showing:

- Request rate and latency (p50/p95/p99)
- Error rate by endpoint
- Active Celery tasks
- DB connection pool status

Access Grafana at `http://localhost:3001` (default credentials: `admin` / `admin`).

---

## Kubernetes Deployment

Manifests are in `deployment/kubernetes/` using Kustomize:

```bash
kubectl apply -f deployment/kubernetes/base/
```

The `backend.yaml` deploys the FastAPI service and `vllm.yaml` deploys the inference server with GPU resource reservations. Overlays can be added under `deployment/kubernetes/overlays/` for staging/production environments.

---

## Configuration Reference

All settings are in `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Set to `production` to disable `/docs` |
| `SECRET_KEY` | `change-me` | JWT signing key — change this |
| `LLM_MODEL` | `meta-llama/Meta-Llama-3-8B-Instruct` | Model served by vLLM |
| `EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Sentence embedding model |
| `VLLM_BASE_URL` | `http://vllm:8000/v1` | OpenAI-compatible inference URL |
| `QDRANT_COLLECTION` | `enterprise_knowledge` | Primary vector collection name |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j connection |
| `HF_TOKEN` | — | HuggingFace token for gated models |
| `GIT_REPOS_PATH` | `/data/repos` | Where git repos are cloned |

---

## Security Notes

- Passwords are hashed with bcrypt.
- All API endpoints (except auth) are protected by JWT bearer tokens.
- The audit middleware logs every request with method, path, status code, and duration.
- In production, set `APP_ENV=production` (disables Swagger UI) and use a strong `SECRET_KEY`.
- The CORS middleware currently allows `*` — restrict this to your frontend domain in production.

---

## Limitations & Known Gaps

- `ingest_git_repo` and `ingest_document` pipeline methods are stubbed (`NotImplementedError`) — the ingestion framework and API layer are complete but the full parser-to-storage wiring is in progress.
- The fine-tuning dataset builder produces placeholder outputs for code examples — human review or LLM-assisted annotation is needed before training.
- vLLM requires an NVIDIA GPU; no CPU-only inference fallback is included.
- Conversation history is tracked by `conversation_id` but multi-turn context window management is not yet implemented in the agent state.

---

## Contributing

1. Fork the repo and create a feature branch.
2. Run `ruff check backend/` before opening a PR.
3. Add tests under `backend/tests/` for any new service logic.
4. Open a PR against `develop`.
