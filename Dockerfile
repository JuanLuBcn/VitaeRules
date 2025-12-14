FROM python:3.12-slim as builder

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to create virtual environment in the project directory
RUN poetry config virtualenvs.in-project true

# Install dependencies (without dev dependencies)
RUN poetry install --only main --no-root

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies (if any specific system libs are needed)
# curl is useful for healthchecks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
# Copy environment files (using wildcard to match .env if it exists, and .env.example)
COPY .env* ./

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV APP_ENV=prod

# Create data directory
RUN mkdir -p data

# Run the application
CMD ["python", "-m", "app.main"]
