FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files needed for installation
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package and its dependencies
RUN uv pip install --system --no-cache .

FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy templates (not included in the wheel)
COPY src/life/templates/ /usr/local/lib/python3.12/site-packages/life/templates/

# Create non-root user
RUN useradd -m -u 1000 app && mkdir -p /data && chown app:app /data
USER app

EXPOSE 8000

CMD ["uvicorn", "life.main:app", "--host", "0.0.0.0", "--port", "8000"]
