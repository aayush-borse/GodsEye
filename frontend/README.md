# GOD'S EYE — SIH26067 Ocean Intelligence Frontend

React + Vite upload/session shell with the IO·MODEL scientific explorer.

## Development

```bash
npm install
npm run dev
```

The Vite server runs on `http://127.0.0.1:5173` and proxies API calls to the FastAPI backend on port 8000.

## Production

```bash
npm install
npm run build
```

FastAPI serves `dist/index.html` and the explorer at `/ocean.html`.
