"""Convenience launcher for GOD\'S EYE."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("ocean_backend.api.main:app", host="127.0.0.1", port=8000, reload=False)
