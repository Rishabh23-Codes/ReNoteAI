# ReNote AI — Document Chat Backend

A FastAPI-based backend service that lets authenticated users upload documents (PDF or TXT) and chat with them using a **RAG (Retrieval-Augmented Generation)** pipeline powered by FAISS, HuggingFace embeddings, and Groq LLM.

---

## Table of Contents

- [Features](#features)
- [Tech Stack & Design Decisions](#tech-stack--design-decisions)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running the Server](#running-the-server)
- [API Reference](#api-reference)
- [Security Practices](#security-practices)


---

## Features

- **User Registration & JWT Authentication** — Secure token-based auth with bcrypt password hashing
- **Document Upload** — Supports `.pdf` and `.txt` files, scoped per user
- **RAG Pipeline** — Documents are chunked, embedded, and stored in a FAISS vector index
- **Chat / Q&A** — Ask natural language questions; answers are grounded in uploaded document content
- **Document Management** — Delete the active document to free up the index

---

## Tech Stack & Design Decisions

| Component | Choice | Reason |
|---|---|---|
| **Framework** | FastAPI | Async-first, auto-generates OpenAPI docs, clean dependency injection |
| **Auth** | JWT via `python-jose` + `passlib[bcrypt]` | Industry-standard stateless auth; bcrypt is slow-by-design making brute-force costly |
| **Database** | SQLite + SQLAlchemy | Zero-config relational DB sufficient for a local assignment; swap to Postgres with one URL change |
| **Embeddings** | `all-MiniLM-L6-v2` (HuggingFace) | Runs fully locally, no API cost, excellent speed/quality tradeoff for semantic search |
| **Vector Store** | FAISS (local) | In-process, no external service needed, persisted to disk per user |
| **LLM** | Groq `llama-3.3-70b-versatile` | Near-zero latency inference (~500 tokens/s), free tier available, strong instruction following |
| **Text Splitting** | `RecursiveCharacterTextSplitter` | Respects natural text boundaries (paragraphs → sentences → words), minimises context bleed |
| **PDF Loading** | `PyPDFLoader` | Lightweight, handles multi-page PDFs without heavy dependencies |

**Why FAISS over a hosted vector DB?**  
For a local-first assignment, FAISS is simpler (no Docker service, no API key) and fast enough for single-user document search. For production, swap to Qdrant or Pinecone.

**Why Groq over OpenAI?**  
Groq delivers significantly lower latency at comparable quality, and the free tier covers development usage comfortably.

---

## Project Structure

```
renote-ai/
│
├── main.py              # FastAPI app — routes for auth, upload, chat, delete
├── auth.py              # JWT token logic, password hashing, user models
├── database.py          # SQLAlchemy models and DB engine setup
├── retrieval.py         # RAG pipeline — document processing, FAISS indexing, Q&A
│
├── vector_stores/       # Auto-created; stores per-user FAISS indexes
│   └── {username}/
│       └── active_index/
│
├── renote_ai.db         # Auto-created SQLite database
├── .env                 # Environment variables (not committed)
├── requirements.txt     # Python dependencies
└── README.md
```

---

## Prerequisites

- Python **3.10+**
- A [Groq API key](https://console.groq.com/) (free tier available)
- `pip` or a virtual environment manager

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Rishabh23-Codes/ReNoteAI.git
cd ReNoteAI
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Required: your Groq API key
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Required: a long random string for signing JWTs
SECRET_KEY=your_super_secret_key_here
```

---

## Running the Server

```bash
uvicorn main:app --reload
```

The server starts at **`http://127.0.0.1:8000`**

Interactive API docs (Swagger UI) are auto-available at:  
**`http://127.0.0.1:8000/docs`**

---

## API Reference

### Authentication

#### `POST /register` — Register a new user

**Request Body (JSON):**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "full_name": "Alice Smith",
  "disabled": true,
  "password": "securepassword123"
}
```

**Response `200`:**
```json
{
  "message": "User registered"
}
```

**Response `400`** — Username already exists.

---

#### `POST /token` — Log in and get a JWT token

**Request Body (`application/x-www-form-urlencoded`):**
```
username=alice&password=securepassword123
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
  "token_type": "bearer"
}
```

**Response `401`** — Invalid credentials.

> Use the returned `access_token` as a `Bearer` token in the `Authorization` header for all subsequent requests.

---

### Document Management

#### `POST /upload` — Upload a document

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:** `multipart/form-data` with a `file` field containing a `.pdf` or `.txt` file.

**Response `200`:**
```json
{
  "message": "New document uploaded."
}
```

**Response `400`** — Unsupported file type.

> Uploading a new document replaces the previous one. Each user has exactly one active document at a time.

---

#### `DELETE /document` — Delete the active document

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response `200`:**
```json
{
  "message": "Document deleted successfully."
}
```

**Response `404`** — No document found to delete.

---

### Chat

#### `POST /chat` — Ask a question about the uploaded document

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameter:**
```
?query=What is the main topic of this document?
```

**Response `200`:**
```json
{
  "answer": "The document primarily discusses...",
  "sources": [
    { "source": "my_file.pdf", "page": 2 },
    { "source": "my_file.pdf", "page": 5 }
  ]
}
```

> If no relevant content is found, the answer will be: `"I'm sorry, I couldn't find an answer in your documents."`  
> If no document has been uploaded yet: `"No active document found. Please upload one first."`


## Security Practices

- **Passwords** are hashed with `bcrypt` before storage — plaintext passwords are never persisted
- **JWT tokens** are signed with a secret key using HS256; tokens expire after 15 minutes by default
- **User isolation** — vector indexes are stored under `vector_stores/{username}/`, ensuring one user cannot access another's data
- **File validation** — only `.pdf` and `.txt` extensions are accepted; the temp file is deleted immediately after processing
- **Environment variables** — all secrets (`SECRET_KEY`, `GROQ_API_KEY`) are loaded from `.env`, never hardcoded



