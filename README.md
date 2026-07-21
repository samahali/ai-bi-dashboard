# 🤖 AI-Powered Business Intelligence Dashboard

A full-stack application that lets you upload data files (CSV, Excel, JSON) and interact with them using **natural language** — powered by **LangChain**, a Watsonx/OpenAI-backed **Text-to-SQL AI Agent**, and **ChromaDB-based retrieval** for schema context.

Built with **ReactJS + Vite** on the frontend and **FastAPI** on the backend.

---

## ✨ Features

- 📁 **Data Upload** — Upload CSV, Excel (.xlsx), and JSON files
- 💬 **Natural Language Queries** — Ask plain English questions, get SQL-powered answers, via a LangChain-orchestrated agent
- 🔎 **RAG-Based Schema Retrieval** — ChromaDB retrieves the columns relevant to your question instead of always sending the full schema to the LLM
- 📊 **Auto-Generated Charts** — Line, bar, pie, and scatter charts via Recharts
- 🔮 **Statistical Anomaly & Trend Detection** — Z-score outliers, missing-data, and skew detection on your data
- 📝 **PDF Report Generation** — Pick queries and/or insights, generate a report with one click
- 🔐 **JWT Authentication** — Secure register/login/logout flow
- 🐳 **Fully Dockerized** — One command to run everything

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | ReactJS, Vite, TailwindCSS, React Query, Recharts |
| Backend | FastAPI, Python 3.12, SQLAlchemy, Alembic |
| AI | LangChain, Watsonx (Granite) / OpenAI fallback |
| Database | PostgreSQL 15, ChromaDB (schema RAG vector store) |
| Auth | JWT (python-jose), bcrypt |
| Parsing | Pandas, openpyxl |
| Reports | ReportLab (PDF) |
| DevOps | Docker, docker-compose, Nginx |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone & Configure

```bash
git clone <your-repo>
cd bi-dashboard-ai
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker

```bash
docker compose up --build
```

That's it! The app will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🔑 Environment Variables

See [`.env.example`](.env.example) for all required environment variables.

Key variables:
```env
# Watsonx (primary LLM provider)
WATSONX_APIKEY=your_watsonx_apikey
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=your_project_id

# OpenAI (fallback)
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/bi_dashboard

# JWT — set this explicitly; it defaults to a random value generated at
# process start if unset, which invalidates all tokens on every restart
SECRET_KEY=your-super-secret-jwt-key
```

---

## 📁 Project Structure

```
bi-dashboard-ai/
├── backend/          # FastAPI Python backend
├── frontend/         # React + Vite frontend
├── nginx/            # Nginx reverse proxy config
├── docs/             # Project documentation
├── scripts/          # Utility scripts
└── docker-compose.yml
```

---

## 📖 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Security](docs/SECURITY.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Deployment](docs/DEPLOYMENT.md)

---

## 🎓 Technologies Demonstrated

- ✅ LLM integration (Watsonx / Granite, OpenAI fallback)
- ✅ LangChain-orchestrated AI agent for text-to-SQL
- ✅ RAG (Retrieval-Augmented Generation) with ChromaDB for schema retrieval
- ✅ Text-to-SQL with prompt engineering
- ✅ Prompt injection prevention
- ✅ Full-stack Docker deployment

---

## 👤 Author

Built by Samah Ali as a portfolio project for Full-Stack + AI roles.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://linkedin.com/in/samah-ali8)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black)](https://github.com/samahali)
