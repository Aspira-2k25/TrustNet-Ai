# TrustNet AI — Team Setup Guide 🚀

Yeh guide teammates ke liye hai taaki bina kisi error ke project setup aur run ho sake.

---

## 📌 Prerequisites (Pehle Yeh Install Karein)

1. **Python 3.11**: [Download Python 3.11](https://www.python.org/downloads/)
   > ⚠️ **Important**: Installation ke time par **"Add python.exe to PATH"** checkbox zaroor tick karein!
2. **Node.js (v18 ya v20+)**: [Download Node.js](https://nodejs.org/)
3. **Git**: [Download Git](https://git-scm.com/)

---

## ⚡ Option A: Automatic 1-Click Setup (Recommended / Sabse Aasan)

Terminal ya Command Prompt kholein project root folder mein aur sirf yeh ek command run karein:

```cmd
.\setup.bat
```

Yeh script automatically:
- Dono Python virtual environments (`.venv` aur `.venv-scam`) banata hai
- Compatible PyTorch CPU aur sari python dependencies install karta hai
- Frontend dependencies (`npm install`) install karta hai
- Model integrity check verify karta hai

Setup complete hone ke baad direct **Project Start** section par jayein.

---

## 🛠️ Option B: Step-by-Step Manual Setup

Agar aap manual commands run karna chahte hain, toh neeche diye gaye steps follow karein:

### Step 1: PowerShell Execution Policy Allow Karein
Agar PowerShell script run karne par *“running scripts is disabled on this system”* error aaye, toh terminal me pehle yeh run karein:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

### Step 2: Main Python Environment (`.venv`) Banayein

```powershell
# Virtual environment create karein
python -m venv .venv

# Sari microservice dependencies install karein
.\install-deps.bat
```

---

### Step 3: Scam Detection Environment (`.venv-scam`) Banayein

```powershell
powershell -ExecutionPolicy Bypass -File .\install-scam.ps1
```

---

### Step 4: Frontend Dependencies Install Karein

```powershell
cd frontend
npm install
cd ..
```

---

### Step 5: Model Integrity Verify Karein

```powershell
.\.venv-scam\Scripts\python.exe verify-scam.py
```
> Screen par `"integrity": "PASS"` aana chahiye.

---

## ▶️ Project Kaise Chalayein (Run the Project)

Setup ho jane ke baad project start karne ke liye:

```cmd
.\start-dev.bat
```

Command run hote hi sabhi microservices aur frontend start ho jayenge:
- 🌐 **Web Dashboard:** [http://localhost:5173](http://localhost:5173)
- 🔌 **API Gateway:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 🛡️ **Auth Service:** [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)
- 🔍 **Scan Management:** [http://127.0.0.1:8002/health](http://127.0.0.1:8002/health)
- 🖼️ **Image Deepfake API:** [http://127.0.0.1:8003/health](http://127.0.0.1:8003/health)
- ⚖️ **Trust Engine:** [http://127.0.0.1:8004/health](http://127.0.0.1:8004/health)
- 📩 **Scam Message Service:** [http://127.0.0.1:8005/ready](http://127.0.0.1:8005/ready)

---

## ⏹️ Project Kaise Band Karein (Stop Services)

Jab bhi project stop karna ho:

```cmd
.\stop-dev.bat
```

Yeh saare background services aur listening ports (8000–8005, 5173) cleanly band kar dega.

---

## 🔄 Project Restart Karna Ho Toh:

```cmd
.\start-dev.bat --restart
```

---

## ❓ Common Errors & Solutions

### Error 1: `running scripts is disabled on this system`
**Karan:** Windows PowerShell default policy scripts block karti hai.  
**Solution:** PowerShell me yeh run karein:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Error 2: `Ports already in use: 8000, 8001...`
**Karan:** Purane background processes abhi bhi chal rahe hain.  
**Solution:**
```cmd
.\stop-dev.bat
```
Phir dubara `.\start-dev.bat` chalayein.

### Error 3: `Scam artifact checksum mismatch`
**Karan:** Windows Git ne clone karte waqt `vocab.txt` ya `tokenizer.json` ki line endings CRLF me convert kar di.  
**Solution:**
```powershell
powershell -Command "Get-ChildItem -Path 'models\scam_message\artifacts\*' -File | ForEach-Object { $b = [System.IO.File]::ReadAllBytes($_.FullName); $text = [System.Text.Encoding]::UTF8.GetString($b); if ($text.Contains(\"`r`n\")) { $clean = $text.Replace(\"`r`n\", \"`n\"); [System.IO.File]::WriteAllBytes($_.FullName, [System.Text.Encoding]::UTF8.GetBytes($clean)); Write-Host ('Fixed: ' + $_.Name) } }"
```
Aur phir `.\.venv-scam\Scripts\python.exe verify-scam.py` run karein.
