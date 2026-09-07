# FinRLExtention Frontend

React + Vite chat interface for the FinRLExtention report pipeline. Ask about a
ticker, watch the backend assemble the report, then preview or download the
resulting PDF without leaving the page.

## Running

```bash
npm install
npm run dev
```

Dev server: `http://localhost:5173`. The FastAPI backend must be running on
port 8000 — start it from the project root first:

```bash
python -m uvicorn src.backend.app:app --reload --port 8000
```

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | ESLint |

## Layout

| File | Role |
| --- | --- |
| `src/main.jsx` | Entry point — mounts `App`. |
| `src/App.jsx` | Thin shell around `Frontend`. |
| `src/Frontend.jsx` | Everything that matters: conversation state, sidebar, ticker suggestions, backend calls. |
| `src/PdfPreviewOverlay.jsx` | Full-screen PDF reader — `react-pdf`, zoom, keyboard nav, page tracking via `IntersectionObserver`. |
| `src/App.css` | Component styles. |
| `src/index.css` | Base page styles. |

## Talking to the backend

`API_BASE` is hardcoded to `http://localhost:8000` in both `Frontend.jsx` and
`PdfPreviewOverlay.jsx`. Change it in both places when pointing at a deployed
backend, and set `FRONTEND_ORIGIN` on the backend so CORS allows the new origin.

Three endpoints are used:

- `POST /api/chat` — sends `{message, history}`. Only prior turns go in
  `history`; the current message is passed separately. A response carrying a
  `pdf_filename` means a report was generated.
- `GET /api/reports` — populates the sidebar report list.
- `GET /api/report/download/{filename}` — backs both preview and download.

Conversations live in React state only. Reloading the page clears them; the
report list survives because it is re-fetched from the backend.
