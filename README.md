
<div align="center">
  <img src="docs/assets/logo.jpeg" alt="SigmaTechno Logo" width="400" />
</div>

<p align="center">
  <strong>Modern, High-Performance FastAPI Backend with RBAC</strong>
</p>

<p align="center">
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic"></a>
</p>

# 🚀 Overview

**SigmaTechno** is a production-ready asynchronous backend service built with **FastAPI**. It is designed for scalability, security, and developer experience, featuring a robust Role-Based Access Control (RBAC) system and comprehensive authentication.

The architecture follows modern best practices including **SOLID** principles, strictly typed Python, and **OWASP Top 10** security guidelines.

# ✨ Key Features

*   **⚡ High Performance**: Leveraging Starlette and Pydantic for lightning-fast execution.
*   **🔒 Enterprise Security**:
    *   **JWT Authentication**: Secure stateless authentication using `python-jose` with **Refresh Token** rotation.
    *   **Password Hashing**: Industry-standard Argon2/Bcrypt hashing.
    *   **OWASP Compliance**: Secure by design (input validation, sanitization, secure headers).
*   **👤 Robust RBAC**: Granular permission control via `Role` entity (e.g., Admin, Editor, User) and scopes.
*   **🗄️ Modern Database Stack**:
    *   **Async Interface**: Using `asyncpg` for non-blocking I/O.
    *   **SQLAlchemy 2.0**: Latest ORM features and type safety.
    *   **Alembic**: Robust database migrations.
    *   **Soft Deletes**: `deleted_at` support for auditability and data recovery.
*   **🐳 Container Native**: Full Docker & Docker Compose support for simplified deployment.
*   **✅ Testing**: Integrated `pytest` suite and smoke tests.

# 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **Database** | [PostgreSQL](https://www.postgresql.org/) |
| **ORM** | [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/) |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Auth** | JWT (JSON Web Tokens) |
| **Environment** | Docker / Python 3.12+ |

# 📋 Feature Checklist

| # | Feature | Status | Notes |
|---|:---|:---:|:---|
| 1 | Install & running lokal (uvicorn) | ✅ Ready | See [Running Locally](#-running-locally) section |
| 2 | Public endpoint | ✅ Done | `/health/`, `/posts`, `/posts/{slug}` (public read) |
| 3 | Private endpoint (must login) | ✅ Done | `/users/me`, POST `/comments` require auth |
| 4 | CRUD ke DB pakai ORM | ✅ Done | `CRUDBase` in `app/crud/base.py` |
| 5 | CRUD ke DB pakai raw SQL | ⚠️ Partial | Implemented for subscriber read in `CRUDSubscriber.get_by_email()` using parameterized raw SQL |
| 6 | Caching ke Redis | ✅ Done | Cache-aside pattern in `app/core/cache.py` |
| 7 | Middleware autentikasi & otorisasi | ⚠️ Partial | Auth via `Depends()`, CORS middleware exists |
| 8 | Upload file | ❌ Missing | Not implemented yet |
| 9 | Download file | ❌ Missing | Not implemented yet |
| 10 | Decorator manajemen akses role | ✅ Done | `RoleChecker` dependency in `app/api/dependencies.py` |

**Summary**: 5 ✅ completed, 2 ❌ missing, 3 ⚠️ partial.

# 🏁 Getting Started

## Prerequisites

*   **Docker & Docker Compose** (Recommended)
*   *Alternatively*: Python 3.12+ and a local PostgreSQL instance.

## Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/SigmaTechno.git
    cd SigmaTechno
    ```

2.  **Environment Setup**
    ```bash
    cp .env.example .env
    # Update .env with your specific configuration
    ```

## 🏃‍♂️ Running with Docker (Recommended)

Build and start the entire stack:

```bash
docker-compose up --build
```

The application will be available at `http://localhost:8000`.

## 🔧 Running Locally

If you prefer running without Docker:

1.  **Create and activate virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run Migrations**
    ```bash
    alembic upgrade head
    ```

4.  **Start the Server**
    ```bash
    uvicorn app.main:app --reload
    ```

# 📚 Documentation

*   **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
*   **Internal Docs**: See the [`docs/`](./docs/) directory for architectural decisions and API contracts.

# 🤝 Contributing

We follow strict coding standards to ensure quality and maintainability. Please review our guidelines before contributing:

*   **Documentation**: Please refer to the [`docs/`](./docs/) directory for detailed architectural principles, coding standards, and API contracts.x
