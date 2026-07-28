# 🤖 RAG-Based AI Chatbot

A Retrieval-Augmented Generation (RAG) based AI Chatbot built using **Python**, **LangGraph**, **FastAPI**, **Pinecone**, and **Google Gemini**. The chatbot answers user queries **strictly based on the provided knowledge base** by retrieving relevant document chunks before generating a response.

## 🚀 Live Demo

**Frontend (Vercel):**  
https://chat-bot-blue-kappa.vercel.app/

**Backend API (Render):**  
https://chat-bot-2bhi.onrender.com/

---

## 📌 Features

- 📄 PDF document ingestion
- ✂️ Automatic text chunking
- 🔍 Semantic search using vector embeddings
- 🗄️ Pinecone Vector Database integration
- 🧠 LangGraph-powered RAG workflow
- 🤖 Google Gemini LLM for answer generation
- ⚡ FastAPI backend
- 💬 React-based chat interface
- 📖 Answers generated only from the uploaded knowledge base
- 📊 Returns retrieved context and confidence score

---

## 🛠️ Tech Stack

### Backend
- Python
- FastAPI
- LangGraph
- LangChain
- Google Gemini
- Pinecone
- HuggingFace Embeddings

### Frontend
- React
- Vite
- Tailwind CSS

### Deployment
- Vercel (Frontend)
- Render (Backend)

---

## 📂 Project Structure

```
Chat_Bot/
│
├── backend/
│   ├── app.py
│   ├── graph.py
│   ├── ingest.py
│   ├── retriever.py
│   ├── config.py
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/gaganthakre2026/Chat_Bot.git

cd Chat_Bot
```

---

### 2. Backend Setup

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

---

### 3. Configure Environment Variables

Create a `.env` file inside the backend folder.

```env
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
PINECONE_API_KEY=YOUR_PINECONE_API_KEY
PINECONE_INDEX_NAME=YOUR_INDEX_NAME
```

---

### 4. Ingest the Knowledge Base

```bash
python ingest.py
```

---

### 5. Run Backend

```bash
uvicorn app:app --reload
```

Backend runs at

```
http://localhost:8000
```

---

### 6. Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

Frontend runs at

```
http://localhost:5173
```

---

# 🏗️ Architecture

```
                PDF Knowledge Base
                        │
                        ▼
               Text Extraction
                        │
                        ▼
                Text Chunking
                        │
                        ▼
              Generate Embeddings
                        │
                        ▼
                Pinecone Vector DB
                        │
────────────────────────────────────────────

                 User Question
                        │
                        ▼
             Convert to Embedding
                        │
                        ▼
         Retrieve Similar Chunks
                        │
                        ▼
                  LangGraph
                        │
                        ▼
             Google Gemini LLM
                        │
                        ▼
               Final Response
                        │
                        ▼
 Answer + Context + Confidence Score
```

---

# 📋 Sample Queries

1. What is Agentic AI?

2. What are AI Agents?

3. Explain the architecture of Agentic AI.

4. What are the benefits of Agentic AI?

5. What are the limitations of Agentic AI?

6. How does Agentic AI differ from traditional AI?

---

## 📤 API Response

```json
{
  "answer": "Generated answer based on retrieved context.",
  "context": [
    "...retrieved chunk 1...",
    "...retrieved chunk 2..."
  ],
  "confidence": 0.94
}
```

---

## 📖 Knowledge Base

The chatbot is built using the following knowledge source:

**Agentic AI eBook**

https://konverge.ai/pdf/Ebook-Agentic-AI.pdf

---

## 📸 Demo

**Live Application**

https://chat-bot-blue-kappa.vercel.app/

---

## 👨‍💻 Author

**Gagan Thakre**

GitHub: https://github.com/gaganthakre2026

LinkedIn: https://www.linkedin.com/in/gagan-thakre

---

## 📄 License

This project is created for educational and interview evaluation purposes.
