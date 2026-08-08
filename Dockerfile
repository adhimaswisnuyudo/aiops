# AIOps Agent — Docker Image
# Base: Python 3.11-slim + SSH client
FROM python:3.11-slim

LABEL org.opencontainers.image.title="aiops-agent"
LABEL org.opencontainers.image.description="AI-powered DevOps/SRE assistant"
LABEL org.opencontainers.image.version="0.1.0"

# Install system dependencies (OpenSSH client)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-client \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directories
RUN mkdir -p /app /app/data

WORKDIR /app

# Copy source code
COPY pyproject.toml .
COPY aiops_agent/ ./aiops_agent/
COPY playbooks/ ./playbooks/
COPY config.example.yaml ./config.example.yaml
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# Install dependencies + package in editable mode
RUN pip install --no-cache-dir -e ".[dev]"

# Default: interactive REPL mode (override with CLI args)
ENTRYPOINT ["./docker-entrypoint.sh", "aiops"]
CMD ["repl"]
