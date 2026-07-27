# Product Requirements Document (PRD)
## PDF-Grounded RAG Chatbot

**Version:** 1.0
**Date:** July 27, 2026
**Owner:** Gagan

---

## 1. Purpose

Build a chatbot application that allows a user to upload a PDF document and ask natural-language questions about its content. The bot must answer **strictly grounded in the PDF** — no hallucinated or external knowledge — and must show the user which parts of the document were used to generate the answer, along with a confidence score.

## 2. Problem Statement

Reading long PDFs (reports, manuals, research papers, contracts) to find specific answers is slow. Generic LLM chatbots either don't have access to the document or hallucinate answers not actually present in it. Users need a tool that:
- Lets them upload any PDF
- Answers questions using only that PDF's content
- Is transparent about *where* the answer came from
- Tells them how confident the system is in the answer

## 3. Goals & Objectives

| Goal | Description |
|---|---|
| Accurate retrieval | Return the most relevant chunks from the PDF for a given query |
| Grounded generation | LLM answers must be traceable to retrieved chunks only |
| Transparency | Every answer is shown with its source chunks and a confidence score |
| Usability | Simple chat interface — upload once, ask multiple questions |
| Extensibility | Architecture should support multiple documents / users later |

## 4. Target Users

- Students and researchers digesting long papers
- Professionals working with contracts, manuals, SOPs, policy documents
- Gagan's own portfolio/demo project — showcasing full-stack + AI/RAG skills for internship applications

## 5. Core Features (Functional Requirements)

### 5.1 Document Ingestion
- FR1: User can upload a PDF file via the React UI.
- FR2: Backend extracts text from the PDF.
- FR3: Text is split into overlapping chunks (configurable size/overlap).
- FR4: Each chunk is embedded and stored in Pinecone with metadata (document id, page number, chunk index).
- FR5: Document metadata (filename, upload date, owner, status) is stored in Supabase.

### 5.2 Chat / Q&A
- FR6: User can type a question in a chat interface.
- FR7: System retrieves top-k relevant chunks from Pinecone (scoped to the active document).
- FR8: LangGraph pipeline generates an answer using only retrieved chunks as context.
- FR9: If no relevant chunk is found above a similarity threshold, the bot must respond "I couldn't find this in the document" rather than guessing.
- FR10: Each response includes:
  - Final answer (text)
  - Retrieved context chunks (text + page number + similarity score)
  - Overall confidence score for the answer
- FR11: Chat history is persisted per user/session in Supabase and viewable on reload.

### 5.3 User Management (minimal)
- FR12: Supabase Auth for login/signup (email or magic link).
- FR13: Each user only sees their own uploaded documents and chat history.

### 5.4 Frontend (React)
- FR14: PDF upload screen with upload progress/status.
- FR15: Chat window (message bubbles: user vs bot).
- FR16: Expandable "Sources" panel under each bot answer showing retrieved chunks, page numbers, and scores.
- FR17: Confidence indicator (e.g., High/Medium/Low badge or numeric %).
- FR18: Document list/switcher if user has multiple PDFs.

## 6. Non-Goals / Out of Scope (v1)

- Multi-document cross-referencing in a single answer
- OCR for scanned/image-only PDFs (assume text-based PDFs initially)
- Real-time collaborative chat
- Fine-tuning the LLM
- Mobile app (web-responsive only)

## 7. User Stories

1. *As a user*, I want to upload a PDF so the bot can learn its content.
2. *As a user*, I want to ask a question and get an answer based only on the PDF, so I can trust it's not making things up.
3. *As a user*, I want to see the exact text/page the answer came from, so I can verify it myself.
4. *As a user*, I want to know how confident the bot is, so I know whether to double-check the answer.
5. *As a user*, I want my chat history saved, so I can revisit previous Q&A.

## 8. Success Metrics

- Retrieval precision: relevant chunk appears in top-3 for ≥90% of test queries
- Groundedness: 0 hallucinated facts in manual QA review of 50 sample questions
- Latency: answer returned in <6s for a document under 50 pages
- User can go from PDF upload to first answer in <30s (excluding LLM response time)

## 9. Assumptions & Constraints

- PDFs are primarily text-based (not scanned images) for v1
- LLM and embedding calls go through a single provider (e.g., OpenAI or Anthropic) — pluggable later
- Pinecone free/starter tier is sufficient for expected document volume
- Supabase handles both Postgres (metadata/chat history) and Auth

## 10. Milestones (Suggested)

| Phase | Deliverable |
|---|---|
| 1 | PDF ingestion + chunking + Pinecone storage working end-to-end (script/CLI) |
| 2 | LangGraph RAG pipeline (retrieve → generate → grounding check) with test queries |
| 3 | FastAPI endpoints wrapping the pipeline + Supabase integration |
| 4 | React chat UI wired to API |
| 5 | Auth, chat history persistence, polish, deployment |
