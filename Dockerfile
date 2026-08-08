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

# Create non-root user
RUN useradd --create-home --shell /bin/bash aiops && \
    mkdir -p /home/aiops/.ssh /app /app/data && \
    chown -R aiops:aiops /app /home/aiops/.ssh

WORKDIR /app

# Copy source code
COPY pyproject.toml .
COPY aiops_agent/ ./aiops_agent/
COPY playbooks/ ./playbooks/
COPY config.yaml ./config.yaml

# Install dependencies + package in editable mode
RUN pip install --no-cache-dir -e ".[dev]"

USER aiops

# Default: interactive REPL mode (override with CLI args)
ENTRYPOINT ["aiops"]
CMD ["repl"]