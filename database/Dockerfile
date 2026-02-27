FROM postgis/postgis:16-3.4

# Install pgvector
RUN apt-get update && apt-get install -y postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Add initialization script to enable extensions
COPY ./init-extensions.sql /docker-entrypoint-initdb.d/
