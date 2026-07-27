# Technical Requirements Document (TRD)
## PDF-Grounded RAG Chatbot

**Version:** 1.0
**Date:** July 27, 2026
**Companion to:** PRD_PDF_RAG_Chatbot.md

---

## 1. System Architecture

```
┌─────────────┐      HTTPS/REST      ┌───────────────────┐
│  React SPA  │ ───────────────────► │   FastAPI Backend  │
│ (Vite/CRA)  │ ◄─────────────────── │                     │
└─────────────┘                      │  ┌───────────────┐  │
      │                              │  │  LangGraph    │  │
      │ Supabase JS client           │  │  RAG Pipeline │  │
      │ (Auth only)                  │  └──────┬────────┘  │
      ▼                              │         │           │
┌─────────────┐                      │         ▼           │
│  Supabase   │ ◄────────────────────┤   Embedding + LLM   │
│ Postgres +  │   metadata/history    │   Provider (API)   │
│    Auth     │                      └─────────┬──────────┘
└─────────────┘                                │
                                                ▼
                                        ┌───────────────┐
                                        │   Pinecone    │
                                        │ Vector Store  │
                                        └───────────────┘
```

**Key architectural decision:** Supabase = system of record for users, documents metadata, and chat history (structured data). Pinecone = vector store for chunk embeddings only. FastAPI orchestrates both plus the LangGraph pipeline. React never talks to Pinecone or the LLM directly — always through FastAPI.

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), TailwindCSS, Supabase JS client (auth), Axios/Fetch |
| Backend | FastAPI (Python 3.11+), Uvicorn |
| Orchestration | LangGraph (+ LangChain community loaders/splitters) |
| LLM | Pluggable — OpenAI GPT-4o / Anthropic Claude via API |
| Embeddings | OpenAI `text-embedding-3-large` or equivalent |
| Vector DB | Pinecone (serverless index) |
| Relational DB / Auth | Supabase (Postgres + Supabase Auth) |
| PDF Parsing | `pypdf` or `PyMuPDF (fitz)` |
| Deployment | Backend: Render/Railway/Fly.io; Frontend: Vercel/Netlify; Pinecone & Supabase: managed cloud |

## 3. Data Model (Supabase / Postgres)

### `documents`
| Column | Type | Notes |
|---|---|---|
| id | uuid (PK) | |
| user_id | uuid (FK → auth.users) | |
| filename | text | |
| pinecone_namespace | text | one namespace per document for isolation |
| page_count | int | |
| status | text | `processing` / `ready` / `failed` |
| created_at | timestamptz | |

### `chat_sessions`
| Column | Type | Notes |
|---|---|---|
| id | uuid (PK) | |
| user_id | uuid (FK) | |
| document_id | uuid (FK → documents) | |
| created_at | timestamptz | |

### `messages`
| Column | Type | Notes |
|---|---|---|
| id | uuid (PK) | |
| session_id | uuid (FK → chat_sessions) | |
| role | text | `user` / `assistant` |
| content | text | |
| retrieved_chunks | jsonb | array of {text, page, score} |
| confidence | float | 0–1 |
| created_at | timestamptz | |

**Row-Level Security:** Enable RLS on all tables; policies restrict rows to `auth.uid() = user_id` (directly or via join).

## 4. Pinecone Schema

- **Index:** single serverless index, e.g. `pdf-rag-index`, dimension matching the embedding model (e.g., 3072 for `text-embedding-3-large`), metric `cosine`.
- **Namespace:** one per document (`document_id`) for clean isolation and easy deletion.
- **Vector metadata:**
```json
{
  "document_id": "uuid",
  "page_number": 12,
  "chunk_index": 4,
  "text": "raw chunk text (also stored for retrieval display)"
}
```

## 5. Ingestion Pipeline (Backend Service)

1. Receive PDF upload → save temp file → insert `documents` row with `status=processing`.
2. Extract text per page (PyMuPDF) preserving page numbers.
3. Chunk text: recursive character/token splitter, ~500–800 tokens per chunk, ~10–15% overlap.
4. Generate embeddings for each chunk (batched).
5. Upsert vectors into Pinecone under the document's namespace, with metadata.
6. Update `documents.status = ready` (or `failed` with error logged).

## 6. LangGraph RAG Pipeline

Represent the pipeline as a LangGraph `StateGraph` with these nodes:

```
retrieve_node → grade_relevance_node → generate_node → groundedness_check_node → format_response_node
```

**State object:**
```python
class RAGState(TypedDict):
    question: str
    document_id: str
    retrieved_chunks: list[dict]   # {text, page, score}
    answer: str
    confidence: float
    grounded: bool
```

- **retrieve_node**: query Pinecone (namespace = document_id, top_k = 5–8), return chunks + similarity scores.
- **grade_relevance_node**: filter out chunks below similarity threshold (e.g., <0.75); if none pass, short-circuit to a "not found in document" response.
- **generate_node**: call LLM with a strict system prompt (see §8) that forces answers to be derived only from provided chunks, with instruction to cite page numbers.
- **groundedness_check_node**: lightweight self-check — ask the LLM (or use NLI-style heuristic) whether the generated answer's claims are supported by the retrieved chunks. Adjust confidence score accordingly; if unsupported, regenerate or fall back to "insufficient information."
- **format_response_node**: assemble final JSON payload (answer, chunks, confidence).

**Confidence score formula (suggested):** weighted combination of (a) average similarity score of chunks used, (b) groundedness-check pass/fail, (c) LLM self-reported certainty if requested in prompt.

## 7. FastAPI Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/documents/upload` | Upload PDF, trigger ingestion pipeline (async/background task) |
| GET | `/documents` | List user's documents + status |
| DELETE | `/documents/{id}` | Delete document + Pinecone namespace |
| POST | `/chat/{document_id}/message` | Send a question, run LangGraph pipeline, return answer |
| GET | `/chat/{session_id}/history` | Fetch prior messages |
| GET | `/health` | Health check |

**Auth:** All endpoints (except `/health`) require a Supabase JWT in the `Authorization` header; FastAPI validates it via Supabase's public JWKS or `supabase-py`.

### Example response — `POST /chat/{document_id}/message`
```json
{
  "answer": "The warranty period is 12 months from the date of purchase.",
  "confidence": 0.87,
  "retrieved_chunks": [
    {
      "text": "...the product is covered under a 12-month warranty from the date of purchase...",
      "page": 4,
      "score": 0.91
    },
    {
      "text": "...warranty claims must be submitted within 30 days of...",
      "page": 5,
      "score": 0.78
    }
  ],
  "grounded": true
}
```

## 8. Prompt Design (Groundedness Enforcement)

System prompt template for `generate_node`:

```
You are a document Q&A assistant. Answer the user's question using ONLY the
context chunks provided below. Do not use outside knowledge.

Rules:
- If the answer is not present in the context, respond exactly:
  "I couldn't find this in the document."
- Always reference the page number(s) your answer is based on.
- Do not speculate or infer beyond what is explicitly stated.

Context:
{retrieved_chunks}

Question: {question}
```

## 9. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Latency | P95 end-to-end chat response < 6s for docs ≤ 50 pages |
| Scalability | Stateless FastAPI (horizontally scalable); Pinecone/Supabase handle scaling |
| Security | Supabase RLS, JWT auth on all routes, PDF upload size limit (e.g., 20MB), input sanitization |
| Reliability | Ingestion pipeline runs as background task with retry/failure status surfaced to UI |
| Observability | Structured logging (request id, latency, token usage); optional LangSmith tracing for LangGraph |
| Cost control | Cache embeddings per document (don't re-embed on repeat queries); cap top_k and max tokens |

## 10. Deployment

- **Frontend:** Vercel/Netlify, environment variables for Supabase URL/anon key and API base URL.
- **Backend:** Containerized (Docker) FastAPI app on Render/Fly.io/Railway; environment variables for Pinecone API key, LLM API key, Supabase service role key.
- **Secrets:** Never expose Supabase service role key or LLM/Pinecone keys to the frontend — frontend only uses the Supabase anon key for auth.

## 11. Repository Structure (Suggested)

```
pdf-rag-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/            # routers: documents.py, chat.py
│   │   ├── core/           # config, security (JWT validation)
│   │   ├── services/       # ingestion.py, pinecone_client.py, supabase_client.py
│   │   ├── rag/            # langgraph_pipeline.py, prompts.py, state.py
│   │   └── models/         # pydantic schemas
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/     # ChatWindow, MessageBubble, SourcesPanel, UploadForm
│   │   ├── pages/
│   │   ├── lib/supabaseClient.js
│   │   └── api/client.js
│   └── package.json
└── docs/
    ├── PRD_PDF_RAG_Chatbot.md
    └── TRD_PDF_RAG_Chatbot.md
```
