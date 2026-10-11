# TrustNet Scam Portable — local CPU edition

Selected predictor: `message-distilbert-lexical-links-hybrid-4`. English SMS/email training and limited collection evaluation; modern inbox reliability is not established. No Groq key is required. The package contains trained weights, tokenizer, calibration, inference/explainability, authentication, gateway, persistence, compiled website/source and Gmail extension. Other image/audio/video detector weights and services are not included. Their existing website entries are outside this export's scope.

## Windows setup (Python 3.11)

Internet is required once to install Python dependencies (CPU PyTorch from its official index). The supplied model needs no first-run weight/tokenizer download. Node is unnecessary for the compiled website; Node is needed only to edit/rebuild it.

```powershell
Expand-Archive .\TrustNet-Scam-Portable.zip -DestinationPath .\TrustNet-share
Set-Location .\TrustNet-share\TrustNet-Scam-Portable
powershell -ExecutionPolicy Bypass -File .\install-scam.ps1
.\.venv-scam\Scripts\python.exe .\verify-scam.py
powershell -ExecutionPolicy Bypass -File .\start-scam.ps1 -Portable
Start-Process http://localhost:5173
```

Wait for `http://localhost:8005/ready`. Register/sign in on the website; this fresh package starts with a new SQLite database and randomly generated local JWT secret in `.env`. Existing checkout users and databases are not copied. Keep `.env` and `portable-state.sqlite` private. Stop only this launcher's services with `powershell -ExecutionPolicy Bypass -File .\stop-scam.ps1`. Restart with the same `.env` and database to retain accounts/history. Ports 8000,8001,8002,8005,5173 must be available. Kafka is disabled in this standalone synchronous edition; local scans work without Docker.

## API example

Use your real local account, replacing the placeholders; never paste passwords or provider keys into a conversation.

```powershell
$login = @{email='your-account@example.com';password='your-local-password'} | ConvertTo-Json
$auth = Invoke-RestMethod http://localhost:8000/api/v1/auth/login -Method Post -ContentType application/json -Body $login
$headers = @{Authorization=('Bearer ' + $auth.data.access_token)}
$body = @{text='Your appointment is confirmed for tomorrow at 10 AM.'} | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/scans/scam/analyze -Method Post -Headers $headers -ContentType application/json -Body $body
```

For email, choose Email on the website, paste the selected body, optionally subject/claimed sender/reply-to; choose HTML only for pasted markup. Script/style/template content is removed without execution or remote loads. Whole canonical input is capped at 10,000 characters, and oversized input is explicitly rejected. All token windows are assessed; attribution samples up to 12 spans and is partial. Unknown/uncertain is a valid result, not proof of safety.

## Gmail extension

Open `chrome://extensions` or `edge://extensions`, enable Developer mode, **Load unpacked** `extensions/trustnet-mail`. In Options select the fixed localhost gateway and sign in with this package's local account. Reload Gmail and click **TrustNet Scan** on one opened/expanded message. Token storage is extension-session-only; reconnect after expiry/restart. No inbox autoscan, mail modification or provider calls. Outlook Web: manual paste only. Actual live Gmail/Chrome/Edge installation remains unverified; fixture extraction/navigation and real authenticated API communication passed.

## Optional Groq

Local detection and its probability never depend on Groq. Set these backend-only values in `.env` locally, then restart:

```dotenv
SCAM_OPTIONAL_ANALYSIS_ENABLED=true
GROQ_API_KEY=replace-locally-with-your-provider-key
GROQ_MODEL=openai/gpt-oss-20b
```

Website users must additionally tick opt-in per scan. Only bounded existing attribution fragments/notes/values leave the machine, not the full email or headers. The provider can only reorder allowed evidence IDs; no free claims, sender verification, AI percentage or probability changes. Extension keeps this off. Failures/timeouts/429/schema errors retain local results. Provider behavior was tested with mocks; no paid/live provider call was made.

`PACKAGE-MANIFEST.json` lists SHA256 for every payload file. A separate ZIP checksum accompanies the archive. `verify-scam.py` verifies selected model hashes and actual signed masking sensitivity. See the technical handoff and `evaluation.json` for all measured metrics, provenance and limitations. The example JSON files demonstrate usage, not accuracy benchmarks.
