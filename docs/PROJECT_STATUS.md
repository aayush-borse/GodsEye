# GOD'S EYE — implementation and operational notes

Last reviewed: 2026-11-01

## What this repository currently provides

- FastAPI service for NetCDF upload, metadata, bounded data access, diagnostics, model/observation comparison, and renderer-facing binary data.
- xarray-backed model services, interpolation, QC, confidence assessment, and thermocline diagnostics.
- Argo profile ingestion and observation lookup.
- A deterministic, allow-listed natural-language command parser and executor. This is not an unrestricted LLM agent and does not execute arbitrary code.
- React workspace for dataset upload/session inspection, plus the dedicated Three.js scientific explorer in `frontend/public/ocean.html`; both now share a restrained dark editorial visual system.
- Small synthetic 3D/4D model and Argo-like fixtures to make a clean checkout demonstrable.

## Demo data provenance

The files under `src/ocean_backend/data/` are synthetic educational fixtures generated for this repository. The Argo-like profiles are not measurements from actual Argo floats, and the model fields are not operational forecasts or validated ocean reanalysis. They exist to exercise the application workflow and tests. Replace them with authoritative, documented datasets before drawing scientific conclusions.

## Session and storage behavior

- Dataset sessions are held in an in-memory registry. Restarting the backend clears the active registry and users must re-upload their own datasets.
- Uploaded files are written under the process working directory's `data/uploads/` folder. This is local-development storage, not a managed durable data service.
- The current application has no user accounts, per-user authorization, or multi-tenant isolation. Do not expose an untrusted public deployment with private datasets.
- The 1 GB upload ceiling is a technical limit, not a recommendation to upload files of that size to a small free host.

## Visualization dependency

The legacy scientific explorer dynamically imports Three.js from jsDelivr. A network connection is therefore required for the WebGL 3D renderer. The explorer has a fallback path when the 3D renderer cannot initialize, but the visual fallback is not scientific model data. The API remains the source of scientific values.

## Verification performed during this handoff

- `python -m compileall -q src` — passed.
- `python -m pytest -q` — 119 passed.
- FastAPI smoke checks — `/health`, bundled dataset metadata, observation listing, and visualization manifest returned HTTP 200.
- Frontend `npm run build` could not be completed in the handoff environment because npm package downloads from the registry timed out and the required toolchain was not available locally. Run `npm ci` followed by `npm run build` in a normal networked development environment before merging/deploying.
- Ruff was not installed in the handoff environment, so lint status is unverified.

## Recommended next engineering milestones

1. Bundle Three.js through the frontend build rather than relying on a runtime CDN import.
2. Add upload-session persistence/recovery and an explicit dataset deletion/retention workflow.
3. Add authentication/authorization and request/resource limits before any public multi-user deployment.
4. Add an automated frontend build check to CI and run Ruff in CI.
5. Validate scientific behavior against authoritative NetCDF/Argo datasets, including variable naming, CF conventions, calendars, curvilinear grids, missing values, and non-monotonic coordinates.
6. Add integration tests for real upload -> metadata -> volume/slice/vector -> point query -> model/observation comparison workflows.
7. Review the scientific explorer's demo fallback and clearly label it whenever backend data is unavailable.
