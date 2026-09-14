# Trust Net Frontend (frontend)

React + TypeScript + Vite frontend for the Trust Net forensic workstation.

## Stack

- React 19
- TypeScript 6
- Vite 8
- Tailwind CSS 4
- Lucide React
- LM Studio Local Vision AI integration
- Native Web Speech API (100% offline local TTS)

## What It Does

- Auth flows: login/register UI and token persistence in `localStorage`.
- Scan upload flow for multi-signal image forensics.
- Real-time animated progress debrief for CPU-based local vision reasoning.
- Interactive ELA (Error Level Analysis) and Bayer CFA Pixel Morphing canvas studio.
- Comprehensive confidential PDF audit report generation.
- Explainable AI debrief + local speech synthesis through LM Studio and browser SpeechSynthesis.

## API Integration

- Base URL: `VITE_API_GATEWAY_URL` or `http://localhost:8000`
- Main endpoints used:
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/register`
  - `POST /api/v1/scans/analyze`
- Multi-tier Fallback behavior:
  - **Tier 1:** API Gateway at `http://localhost:8000/api/v1/scans/analyze` (with 360s timeout).
  - **Tier 2:** Direct fallback to Scan Management Service at `http://localhost:8002/scans/analyze`.
  - **Tier 3:** Direct fallback to Standalone Deepfake Detector at `http://localhost:8003/detect/file`.

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
- `src/views/` - landing, dashboard, upload, report, auth screens
