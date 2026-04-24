# Project-AgenticEbookLibrary
Agentic Library with RAG. The goal is to include the ebook data in LLM queries by implementing RAG. The main use case is technical information, but it is not limited to it.

## Python environment

From the project root, install the package in editable mode so `domain` and `persistence` resolve everywhere:

```bash
uv sync
```

## Database Setup

The application uses PostgreSQL. ORM models and repositories live in the top-level `persistence` package; schema migrations are managed with [Alembic](https://alembic.sqlalchemy.org/).

### Prerequisites

- PostgreSQL running and a database named `ebooklibrary` created
- `DATABASE_URL` set in your `.env` file:

```
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/ebooklibrary
```

### Apply migrations

Run from the project root:

```bash
uv run alembic -c ingestion/alembic.ini upgrade head
```

### Create a new migration

After changing the ORM model in `persistence/orm/ebook_orm.py`, generate a migration:

```bash
uv run alembic -c ingestion/alembic.ini revision --autogenerate -m "describe_your_change"
```

### Rollback one step

```bash
uv run alembic -c ingestion/alembic.ini downgrade -1
```
