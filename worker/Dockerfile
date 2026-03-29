FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN pip install uv && uv sync --frozen || uv sync

COPY . .

CMD ["uv", "run", "python", "worker.py"]
