# 🇰🇭 Khmer AI Tutor Bot (Serverless Telegram Bot on Vercel)

A 24/7 serverless Telegram AI Tutor bot deployed to **Vercel** powered by **Google Gemini 2.5 Flash** (`google-genai`) and **Microsoft Edge TTS** (`edge-tts`).

---

## ✨ Features

- **24/7 Serverless Webhook:** Runs on Vercel's Python serverless runtime with zero idle cost and no server management.
- **Private Access Control:** Strictly checks `ALLOWED_USER_ID` from environment variables, ignoring unauthorized users.
- **Multimodal Tutoring:**
  - 📝 **Text:** Step-by-step solutions for Grade 1 to University level (Math, Physics, Chemistry, Biology, Khmer Literature).
  - 📷 **Photos:** Homework and exam sheet analysis via Gemini Vision.
  - 🎙️ **Voice-to-Voice:** Listens to Telegram voice notes (`.ogg`), processes audio directly with Gemini 2.5 Flash, and replies with **both text and natural voice speech** using `edge-tts`.
- **Bilingual & Exam-Ready:**
  - Specialized in Cambodian curriculum (BacII / បាក់ឌុប), Teacher Recruitment Exams (ប្រឡងគ្រូ), and Civil Service Exams (ប្រឡងក្របខណ្ឌរដ្ឋ).
  - English conversation partner with real-time grammar corrections.

---

## 📁 Project Structure

```text
├── api/
│   └── index.py          # FastAPI application & Telegram webhook handler
├── test_local.py         # Local integration test suite (Gemini & Edge-TTS)
├── setup_webhook.py      # CLI tool for Telegram webhook management
├── requirements.txt      # Python dependencies
├── vercel.json           # Vercel deployment configuration
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # Project documentation
```

---

## 🚀 Getting Started

### 1. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in the variables:
- `TELEGRAM_BOT_TOKEN`: From [@BotFather](https://t.me/BotFather)
- `ALLOWED_USER_ID`: Your Telegram numeric ID (from [@userinfobot](https://t.me/userinfobot))
- `GEMINI_API_KEY`: From [Google AI Studio](https://aistudio.google.com/)
- `GEMINI_MODEL`: `gemini-2.5-flash`

### 2. Run Local Tests
Install dependencies and run the test suite:
```bash
pip install -r requirements.txt
python test_local.py
```

### 3. Deploy to Vercel
Deploy using the Vercel CLI:
```bash
vercel --prod
```
Set the environment variables in your Vercel Project Dashboard:
- `TELEGRAM_BOT_TOKEN`
- `ALLOWED_USER_ID`
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (optional, defaults to `gemini-2.5-flash`)
- `KHMER_VOICE` (optional, defaults to `km-KH-PisethNeural`)
- `ENGLISH_VOICE` (optional, defaults to `en-US-AriaNeural`)

### 4. Set Webhook
Connect your Telegram Bot to the deployed Vercel URL:
```bash
python setup_webhook.py set https://your-project.vercel.app
```
Verify the webhook status:
```bash
python setup_webhook.py info
```
