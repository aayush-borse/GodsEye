# Frontend build fix

The React frontend requires the React/ReactDOM TypeScript declarations and Vite client declarations.

Run:

```bash
npm install
npm run build
```

Then start the FastAPI application from the project root:

```bash
uv run python run.py
```

Open http://127.0.0.1:8000
