# Third-Party Licences & Attributions

BolKhata is built with open-source software, models, and toolchains. This document catalogs all third-party licences and compliance terms.

---

## 1. Machine Learning Models & Speech Weights

| Model / Library | Maintainer / Source | Licence | Notes |
|---|---|---|---|
| **MLX-Whisper** | Apple MLX Team / mlx-community | MIT Licence | Metal-optimized Whisper inference on Apple Silicon. |
| **OpenAI Whisper Models** | OpenAI | MIT / Apache 2.0 | Weights distributed by OpenAI / Hugging Face under MIT. |
| **RapidFuzz** | Max Bachmann | MIT Licence | Fast string similarity computation in C++ / Cython. |

---

## 2. Backend & Core Dependencies

| Package | Licence | Purpose |
|---|---|---|
| **Python 3.11+** | PSF (Python Software Foundation) Licence | Core runtime platform. |
| **FastAPI** | MIT Licence | High-performance async REST & WebSocket web framework. |
| **Starlette** | BSD 3-Clause Licence | Underlying ASGI toolkit. |
| **Uvicorn** | BSD 3-Clause Licence | Lightning-fast ASGI server implementation. |
| **Pydantic v2** | MIT Licence | Data validation and settings management using Python type annotations. |
| **SQLAlchemy 2** | MIT Licence | Python SQL toolkit and Object Relational Mapper. |
| **Alembic** | MIT Licence | Database migrations tool for SQLAlchemy. |
| **aiosqlite** | MIT Licence | Async SQLite driver. |
| **asyncpg** | Apache 2.0 Licence | Async PostgreSQL driver (for optional production profile). |
| **httpx** | BSD 3-Clause Licence | Next-generation HTTP client for Python. |
| **jiwer** | Apache 2.0 Licence | Word Error Rate (WER) computation library (evaluation harness). |

---

## 3. Frontend Dependencies

| Package | Licence | Purpose |
|---|---|---|
| **React** | MIT Licence | UI component library. |
| **React DOM** | MIT Licence | Browser DOM renderer for React. |
| **TypeScript** | Apache 2.0 Licence | Typed JavaScript superset. |
| **Vite** | MIT Licence | Frontend build tool and dev server. |
| **Lucide React** | ISC Licence | Minimalist, accessible SVG UI icons. |

---

## 4. Development & CI/CD Tooling

| Tool | Licence | Purpose |
|---|---|---|
| **uv** | Apache 2.0 / MIT | Ultra-fast Python package and project manager. |
| **Ruff** | MIT Licence | Extremely fast Python linter and formatter written in Rust. |
| **Mypy** | MIT Licence | Optional static type checker for Python. |
| **Pytest** | MIT Licence | Robust test framework for unit and integration testing. |
| **Pre-commit** | MIT Licence | Framework for managing and maintaining multi-language pre-commit hooks. |
| **detect-secrets** | Apache 2.0 Licence | Enterprise secret baseline scanner. |
