# Use a slim Python image for a smaller footprint
FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies without the project itself to cache layers
RUN uv sync --frozen --no-install-project --no-dev

# Copy the application code
COPY . .

# Install the project
RUN uv sync --frozen --no-dev

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the API port
EXPOSE 8000

# Command to run the application with increased timeout for AI processing
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "60"]
