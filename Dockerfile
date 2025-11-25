# Multi-stage build for optimized production image
FROM python:3.9-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY backend/requirements.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt

# Production stage
FROM python:3.9-slim

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser backend/ .
COPY --chown=appuser:appuser frontend/ ./frontend/

# Switch to non-root user
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "-m", "uvicorn", "app.sliding_window_demo:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]