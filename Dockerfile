# =============================================================================
# JonOps — Autonomous Marketing Agent Container
# =============================================================================
# Base image with Python, Node.js, and Claude Code CLI
# =============================================================================

FROM python:3.11-slim

# Install system dependencies
# chromium + ffmpeg added 2026-05-16 for Almanac video render — HyperFrames
# uses Puppeteer (Chrome DevTools Protocol) for headless composition render,
# then ffmpeg for normalization + audio mux. Both are required for the
# Almanac pipeline (almanac/almanac_pipeline.py) to render mp4s in-container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    jq \
    nodejs \
    npm \
    supervisor \
    chromium \
    fonts-liberation \
    fonts-noto-color-emoji \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Tell Puppeteer (HyperFrames internal dep) to use the system Chromium
# instead of downloading its own ~150MB copy at install time.
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

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
