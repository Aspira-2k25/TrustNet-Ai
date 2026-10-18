# Run the phishing module — existing teammate setup

Use these steps if the full TrustNet application already works on your PC.

1. **Pull the nirmala branch** from the project root:

   ```powershell
   git switch nirmala
   git pull origin nirmala
   ```

2. **Download the phishing model ZIP shared by the project owner:**
   `TrustNet-Phishing-regional-recall-v1.zip`.
   Extract it into the project root. Confirm this file exists:

   ```text
   models/phishing_url/checkpoints/regional_recall_v1/manifest.json
   ```

3. **Verify the installed model:**

   ```powershell
   py -3.11 scripts/package-phishing-team.py --verify
   ```

   Expected: `PASS: regional-recall-v1 manifest and all eight component SHA-256 checksums match.`

4. **Start Docker Desktop** and wait until it is running.

5. **Restart the application** from the project root:

   ```powershell
   .\stop-dev.bat
   .\start-dev.bat
   ```

6. Open **http://localhost:5173**, sign in, select **Phishing/URL Detection**, and submit a new URL.

Keep your existing `.env`, image environment and scam environment. No GPU, retraining or phishing dependency reinstall is needed. Model weights are excluded from Git, so pulling the branch alone does not install them.
