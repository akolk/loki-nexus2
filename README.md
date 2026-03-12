# loki-nexus2

The project is a full-stack data science workspace using Pydantic AI as the core agentic engine, Python (FastAPI) for the backend, and HTML/JS (Leaflet) for the frontend.

## Product Features

- **Pydantic AI engine**: Used to generate Python code based on user questions. The backend executes this code and returns a JSON structured response containing `type` and `content`.
- **Backend agent generated code**: Built with strict geospatial data rules. Performs calculations in EPSG:28992 (RD New) and visualizes data on the map in WGS84 (EPSG:4326). Returns GeoDataFrames directly.
- **Geospatial Processing**: Built with strict geospatial data rules. Performs calculations in EPSG:28992 (RD New) and visualizes data on the map in WGS84 (EPSG:4326).
- **Map Visualization**: The frontend Leaflet map utilizes the PDOK tile server (BRT Achtergrondkaart) for accurate maps of the Netherlands.
- **Tools Integration**: Supports Model Context Protocol (MCP) servers and localized Skill zip files via `pydantic-ai-skills` to dynamically enhance agent capabilities.

## Infrastructure
- Configured using Docker Compose with an Nginx reverse proxy.
- Implements GitHub Actions for multi-platform (linux/amd64, linux/arm64) image builds published to `ghcr.io/akolk`.
- The primary database backend is PostgreSQL with PostGIS and pgvector extensions.
- Includes a local `auth-proxy` for simulating Identity Provider identity headers mapping users to roles.
