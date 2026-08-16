# Trust Net Frontend (frontend)

React + TypeScript + Vite frontend for the Trust Net forensic workstation.

## Stack

- React 19
- TypeScript 6
- Vite 8
- Tailwind CSS 4
- Lucide React
- Optional Puter.js browser SDK integration

## What It Does

- Auth flows: login/register UI and token persistence in `localStorage`.
- Scan upload flow for image analysis.
- Dashboard and report views for forensic output.
- Explainable AI debrief + optional TTS through Puter SDK.

## API Integration

- Base URL: `VITE_API_GATEWAY_URL` or `http://localhost:8000`
- Main endpoints used:
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/register`
  - `POST /api/v1/scans/analyze`
- Fallback behavior:
  - If gateway analyze endpoint is unavailable, frontend tries `http://localhost:8003/detect/file`.

## Development

```bash
npm install
npm run dev
```

## Build And Lint

```bash
npm run build
npm run lint
npm run preview
```

## Environment

Create `.env` in `frontend/` if needed:

```env
VITE_API_GATEWAY_URL=http://localhost:8000
```

## Key Source Paths

- `src/App.tsx` - app shell and view switching
- `src/services/api.ts` - backend API integration
- `src/services/puterAI.ts` - explainability/TTS integration
- `src/views/` - landing, dashboard, upload, report, auth screens
