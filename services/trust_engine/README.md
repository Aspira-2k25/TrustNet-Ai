# Trust Engine Service

The **Trust Engine** is the ultimate authority in the TRUST[NET] microservice cluster. It consumes completed detection reports from all forensic workers (e.g., Image Deepfake Worker, Video Deepfake Worker, Audio Analyzer) and synthesizes a final Weighted Multi-Signal Risk Score.

## Technology Stack
- **Framework**: FastAPI, Python 3.10+
- **Message Broker**: `aiokafka`
- **Data Persistence**: MongoDB (via `motor` asynchronous driver)
- **Caching**: Redis (via `redis.asyncio`)

## The Fusion Logic
In an enterprise setting, a single file may be analyzed by multiple distinct models. The Trust Engine performs the following operations:

1. **Wait & Aggregate**: Listens on the `detector.*.completed` topics. 
2. **Multi-Signal Fusion**: If multiple forensic branches disagree (e.g., Audio says Real, Video says Fake), the Trust Engine applies weighted fusion with contradiction detection to calculate the combined risk assessment.
3. **Verdict Generation**:
   - `0 - 44`: AUTHENTIC (Green)
   - `45 - 74`: SUSPICIOUS (Yellow)
   - `75 - 100`: AI_GENERATED (Red / CRITICAL)
4. **Data Persistence**: Saves the structured report and Evidence Items to the `Scans` collection in MongoDB.
5. **UI Notification**: The API Gateway polls or uses WebSockets to retrieve this final verdict from MongoDB and presents it to the user.

## Running the Service
```bash
uvicorn services.trust_engine.app.main:app --port 8004 --reload
```
