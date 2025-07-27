# Multi-stage build for SF Transit Tracker production deployment
# Optimized for Fly.io with security hardening and performance optimization

# Build stage - dependencies installation
FROM python:3.12-slim as builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Add production dependencies
RUN pip install --no-cache-dir gunicorn==21.2.0 gevent==23.9.1

# Production stage - minimal runtime image
FROM python:3.12-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app

# Set working directory
WORKDIR /home/app

# Copy application code with proper ownership
COPY --chown=app:app . .

# Create data directory for GTFS storage with proper permissions
RUN mkdir -p data && chown -R app:app data

# Create logs directory
RUN mkdir -p logs && chown -R app:app logs

# Switch to non-root user
USER app

# Set environment variables
ENV PYTHONPATH="/home/app"
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Start command using Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-class", "gevent", "--worker-connections", "1000", "--timeout", "30", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "app:app"]