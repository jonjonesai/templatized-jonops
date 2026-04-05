# =============================================================================
# JonOps — Autonomous Marketing Agent Container
# =============================================================================
# Base image with Python, Node.js, and Claude Code CLI
# =============================================================================

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    jq \
    nodejs \
    npm \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create agent user and directories
RUN useradd -m -s /bin/bash agent
WORKDIR /home/agent/project

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=agent:agent . .

# Make scripts executable
RUN chmod +x *.sh *.py scripts/**/*.py 2>/dev/null || true

# Create necessary directories
RUN mkdir -p logs cache tmp sessions \
    && chown -R agent:agent /home/agent

# Copy supervisor config
COPY supervisor/conf.d/*.conf /etc/supervisor/conf.d/

# Switch to agent user
USER agent

# Set environment
ENV HOME=/home/agent
ENV PATH="/home/agent/.local/bin:${PATH}"

# Run post-start script and then supervisor
CMD ["bash", "-c", "bash /home/agent/project/post-start.sh && exec supervisord -n -c /etc/supervisor/supervisord.conf"]
