# Build the React/Vite frontend first.
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN npm install && npm run build

# Run the scientific backend.
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY run.py ./run.py
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
EXPOSE 8000
CMD ["uv", "run", "python", "run.py"]
