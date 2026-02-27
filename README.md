# Pydantic AI Data Science Workspace

A full-stack data science workspace powered by **Pydantic AI**. This project features a robust Python backend (FastAPI), a geospatial data analysis agent using DuckDB, a PostgreSQL state store (with PostGIS and PgVector), and an interactive Map frontend.

## Features

- **Pydantic AI Agentic Engine**:
  - Uses `Deps` to inject User "Soul" (preferences, styling) and database sessions.
  - Retains conversational context by injecting `ChatHistory` from the database.
- **Geospatial Data Analysis**:
  - DuckDB integration via MCP-style tools.
  - Enforces predicate pushdown and lazy loading constraints (LIMITs).
  - Automatic coordinate transformation from `EPSG:28992` (RD New) to `WGS84`.
- **Map Workspace Mode**:
  - Leaflet frontend with PDOK BRT Achtergrondkaart.
  - Floating chat bubble interface.
  - Automatically captures the map bounding box (BBox) to give the agent geographic context.
- **Job Scheduler**:
  - APScheduler implementation for creating recurring research tasks.
- **Dockerized Infrastructure**:
  - Pre-configured `docker-compose.yml` with Nginx reverse proxy, FastAPI backend, and a PostgreSQL database loaded with PostGIS and PgVector.
- **CI/CD**:
  - Multi-platform Docker builds (amd64, arm64) deployed to `ghcr.io` via GitHub Actions.

## Project Structure

```text
.
├── backend/
│   ├── Dockerfile
│   ├── main.py          # FastAPI application
│   ├── agent.py         # Pydantic AI agent logic & tools
│   ├── database.py      # SQLModel engine & session management
│   ├── models.py        # Domain models (User, Soul, ResearchStep, ChatHistory)
│   ├── scheduler.py     # APScheduler service for recurring jobs
│   ├── tools/
│   │   ├── data_tool.py # DuckDB spatial tool
│   │   └── file_tool.py # Sandboxed file tool
│   └── workspace/       # Safe directory for file manipulations
├── frontend/
│   ├── Dockerfile
│   ├── index.html       # Leaflet Map and Chat UI
│   └── app.js           # Client-side logic for API integration
├── database/
│   ├── Dockerfile       # PostGIS image + PgVector
│   └── init-extensions.sql
├── tests/               # Pytest and Playwright verification scripts
├── docker-compose.yml   # Infrastructure orchestration
├── nginx.conf           # Reverse proxy and test header injection
└── requirements.txt     # Python dependencies
```

## Local Development Setup

To run the application locally, you will need Docker and Docker Compose.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd pydantic-ai-workspace
    ```

2.  **Environment Variables:**
    Create a `.env` file in the root directory and add your OpenAI API key (or other provider key if modified):
    ```env
    OPENAI_API_KEY=your-api-key-here
    ```

3.  **Start with Docker Compose:**
    ```bash
    docker-compose up --build -d
    ```

4.  **Access the Application:**
    - Navigate to `http://localhost` in your browser.
    - The Nginx reverse proxy will automatically set test `X-Forwarded-*` headers to simulate an authenticated user (`researcher_01`).

## Testing

To run the test suite locally (requires Python 3.11+):

```bash
pip install -r requirements.txt
pytest tests/
```

To verify frontend integration using Playwright:
```bash
python tests/verify_frontend_map.py
```