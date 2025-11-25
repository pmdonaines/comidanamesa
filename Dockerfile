# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies using uv
# Copy pyproject.toml and uv.lock
COPY pyproject.toml uv.lock ./

# Configure uv to create venv at /venv
ENV UV_PROJECT_ENVIRONMENT="/venv"

# Sync dependencies
# --frozen: ensure uv.lock matches pyproject.toml
# --no-cache: avoid storing cache in the layer
RUN uv sync --frozen --no-cache

# Add /venv/bin to PATH
ENV PATH="/venv/bin:$PATH"

# Copy project
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Run gunicorn
CMD ["uv", "run", "gunicorn", "comidanamesa.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "3000", "--workers", "2", "--threads", "2"]


