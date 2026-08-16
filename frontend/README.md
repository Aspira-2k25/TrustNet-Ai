# TRUST[NET] Frontend Security Workstation

The frontend is a high-performance React application serving as the UI for the TrustNet AI cyber-forensics platform. It allows users to upload media, view scientific analysis breakdowns, and interact with an Explainable AI assistant.

## Technology Stack
- **Framework**: React 18, Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS (with bespoke cyan/neon security aesthetics)
- **Icons**: Lucide React
- **AI Integration**: Puter.js (for GPT-4o Vision & Neural TTS)

## Core Features & Logic
1. **The Canvas Studio (Report View)**: The `ReportView.tsx` component acts as a scientific dashboard. It dynamically parses the `EvidenceItem` array returned from the backend and displays contribution bars for ELA, PRNU, FFT, Physics, and Geometry forensics.
2. **Explainable AI Debriefing**: Uses the `PuterAIService` to take raw JSON telemetry from the deepfake engine and synthesize it into a human-readable threat analysis.
3. **Multimodal Vision Analysis**: The UI securely converts local blobs into base64 images and sends them to the Puter AI Vision pipeline to verify if the physical rendering makes sense to a human observer.

## Running Locally
```bash
npm install
npm run dev
```
