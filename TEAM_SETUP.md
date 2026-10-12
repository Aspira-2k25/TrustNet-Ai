# TrustNet AI — Teammate Setup Guide 🚀

Yeh guide teammates ke liye hai taaki bina kisi error ke project setup aur run ho sake.

---

## 📌 Prerequisites (Zaroori Software)

Setup shuru karne se pehle ensure karein ki yeh installed hain:
1. **Python 3.11**: [Download Python 3.11](https://www.python.org/downloads/)  
   *(⚠️ Install karte waqt **"Add python.exe to PATH"** checkbox par zaroor tick karein)*
2. **Node.js (v18 ya v20+)**: [Download Node.js](https://nodejs.org/)
3. **Git**: [Download Git](https://git-scm.com/)

---

## 📂 Model / Artifacts File Kahaan Rakhna Hai?

Agar aapke paas **`model.safetensors`** file ya poora **`artifacts`** folder hai:

1. Repo ke andar is location par jayein:
   ```
   models\scam_message\artifacts\
   ```
2. **`model.safetensors`** file ko is folder ke andar paste karein.
   *(Agar poora `artifacts` folder mila hai, toh uske andar ki saari files is folder mein paste karein).*

Iske baad neeche diye gaye setup steps follow karein.

---

## 🎯 Case 1: Jinke Paas Image Setup Already Hai (Sirf Scam Module Setup Chahiye)

> 💡 **Fayda:** Is process se aapka **existing image environment (`.venv`) bilkul touch nahi hoga** aur safe rahega.

### ⚡ 1-Click Setup (Sabse Simple):
Terminal / CMD mein yeh run karein:
```cmd
.\setup-scam.bat
```

Yeh script automatically:
- Dedicated `.venv-scam` environment banata hai
- PyTorch CPU aur scam dependencies install karta hai
- `model.safetensors` check karta hai (agar missing ho toh zip se auto-extract kar leta hai)
- Windows line endings (CRLF to LF) automatically theek karta hai
- Model integrity verify karta hai

---

### 🛠️ Ya Manual Step-by-Step Commands:
Agar aapko manual commands run karni hain:

```powershell
# 1. PowerShell me script execution allow karein
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Scam environment create aur install karein
powershell -ExecutionPolicy Bypass -File .\install-scam.ps1

# 3. Agar model.safetensors manually nahi dala, toh zip se unpack karein:
py -3.11 .\install-scam-model.py --package exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip

# 4. Model integrity verify karein
.\.venv-scam\Scripts\python.exe verify-scam.py
```
> Screen par `"integrity": "PASS"` aate hi aapka Scam module 100% ready hai!

---

## 🌟 Case 2: Fresh Teammate (Full Setup - Image + Scam + Frontend)

Agar kisi teammate ko scratch se poora project setup karna hai:

### ⚡ 1-Click Setup:
```cmd
.\setup.bat
```

### 🛠️ Ya Manual Commands:
```powershell
# 1. Permission allow karein
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Main image environment (.venv)
python -m venv .venv
.\install-deps.bat

# 3. Scam module (.venv-scam)
powershell -ExecutionPolicy Bypass -File .\install-scam.ps1

# 4. Frontend dependencies
cd frontend
npm install
cd ..

# 5. Model integrity verify karein
.\.venv-scam\Scripts\python.exe verify-scam.py
```

---

## ▶️ Project Run Kaise Karein (Start All Services)

Setup complete hone ke baad project start karne ke liye:

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

## ⏹️ Project Stop / Restart Kaise Karein

- **Services Band Karne Ke Liye:**
  ```cmd
  .\stop-dev.bat
  ```
- **Clean Restart Karne Ke Liye:**
  ```cmd
  .\start-dev.bat --restart
  ```

---

## ❓ Common Errors & Solutions

### Error 1: `running scripts is disabled on this system`
- **Solution:** PowerShell me run karein:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### Error 2: `Ports already in use: 8000, 8001...`
- **Solution:** Purane background processes stop karne ke liye run karein:
  ```cmd
  .\stop-dev.bat
  ```
  Aur phir `.\start-dev.bat` chalayein.

### Error 3: `Scam artifact checksum mismatch`
- **Solution:** Sirf `.\setup-scam.bat` run kar dein. Yeh script automatically Windows ke line-ending issue ko resolve karke official package verify kar deta hai.
