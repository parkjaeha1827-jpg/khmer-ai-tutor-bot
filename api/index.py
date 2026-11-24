import os
import re
import io
import socket
import logging
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types
import edge_tts

# Ensure fast IPv4 resolution on Windows
old_getaddrinfo = socket.getaddrinfo
def ipv4_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    ipv4_responses = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4_responses if ipv4_responses else responses
socket.getaddrinfo = ipv4_getaddrinfo

load_dotenv(override=True)

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("telegram_tutor_bot")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip()
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "").strip()
KHMER_VOICE = os.getenv("KHMER_VOICE", "km-KH-PisethNeural").strip()
ENGLISH_VOICE = os.getenv("ENGLISH_VOICE", "en-US-AriaNeural").strip()

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_BASE = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"

# System Instruction
SYSTEM_INSTRUCTION = """You are an elite, highly knowledgeable, and patient Cambodian & International AI Tutor (គ្រូបង្រៀន AI ខ្មែរ-អន្តរជាតិ).
Your mission is to help Cambodian and international students, job seekers, and candidates excel in their studies, competitive exams, and language proficiency.

Core Expertise:
1. Academic Curriculum (Grade 1 to University Level):
   - Mathematics (គណិតវិទ្យា): Algebra, Geometry, Calculus, Probability, Vectors, Differential Equations. Always provide complete step-by-step solutions (ដោះស្រាយជាជំហានៗ) with formulas, calculations, and the final answer highlighted.
   - Physics (រូបវិទ្យា): Mechanics, Electricity, Magnetism, Optics, Thermodynamics, Modern Physics with SI units and clear physical interpretations.
   - Chemistry (គីមីវិទ្យា): Chemical equations, balancing, stoichiometry, organic/inorganic chemistry, IUPAC naming, molecular formulas.
   - Biology (ជីវវិទ្យា): Cell biology, genetics, human anatomy, ecology, botany with accurate scientific terms.
   - Khmer Literature (អក្សរសាស្ត្រខ្មែរ): Writing styles, essays, grammar rules, spelling according to the Chuon Nath dictionary, and analysis of Cambodian classical & contemporary literature (e.g., រឿងទុំទាវ, រឿងកុលាបប៉ៃលិន).

2. Competitive Exams & Civil Servant / Teacher Recruitment (ប្រឡងគ្រូ & ប្រឡងក្របខណ្ឌ):
   - Teacher Recruitment Exams (ប្រឡងគ្រូបឋម, អនុវិទ្យាល័យ, វិទ្យាល័យ): Pedagogy (គរុកោសល្យ), teaching methodology, psychology of learning, past exam papers.
   - Civil Service Exams (ប្រឡងក្របខណ្ឌរដ្ឋ): General Knowledge (ចំណេះដឹងទូទៅ), Cambodian Constitution & Law, Geography, History of Cambodia, ASEAN, and international affairs. Provide structured, high-scoring argumentative responses.

3. English Language Coaching & Conversation Partner:
   - Teach English grammar, vocabulary, idioms, IELTS/TOEFL test prep.
   - When the user speaks or writes in English, provide helpful feedback, correct grammatical errors gently, suggest natural phrasing, and maintain an engaging, interactive conversation.

Tone & Style:
- Professional, respectful, encouraging, and pedagogical (ប្រើប្រាស់ពាក្យសមរម្យ រាក់ទាក់ និងលើកទឹកចិត្តសិស្ស).
- Structure your answers with clear headings, bullet points, numbered steps, and bold key concepts.
- When answering questions in Khmer, write natural, fluent, and orthographically correct Khmer.
- When answering in English, use clear, native-level English.
"""

# Lazy-loaded Gemini Client
_gemini_client: Optional[genai.Client] = None

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1beta"})
    return _gemini_client

def call_gemini(contents, system_instruction=SYSTEM_INSTRUCTION) -> str:
    """Call Gemini with automatic model fallback."""
    client = get_gemini_client()
    candidate_models = [GEMINI_MODEL, "gemini-flash-lite-latest", "gemini-3.8-flash"]
    last_error = None
    for model_name in list(dict.fromkeys(candidate_models)):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            if response.text:
                return response.text
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}. Trying next fallback...")
            last_error = e
    if last_error:
        raise last_error
    return "សូមអភ័យទោស ខ្ញុំមិនអាចបង្កើតចម្លើយបានទេ។"

# Helper Functions
def is_user_allowed(user_id: int | str) -> bool:
    if not ALLOWED_USER_ID:
        return True
    allowed_list = [uid.strip() for uid in ALLOWED_USER_ID.split(",") if uid.strip()]
    return str(user_id) in allowed_list

def contains_khmer(text: str) -> bool:
    """Detect if text contains any Khmer unicode characters."""
    return bool(re.search(r"[\u1780-\u17FF\u19E0-\u19FF]", text))

def clean_text_for_tts(text: str) -> str:
    """Strip markdown, LaTeX formulas, and special characters for natural speech synthesis."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]*`", "", text)
    # Remove markdown links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove markdown headers and emphasis
    text = re.sub(r"[#*_~>`]+", "", text)
    # Simplify bullet points
    text = re.sub(r"^[\s]*[-•*]\s+", "", text, flags=re.MULTILINE)
    # Remove excessive blank lines
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

# Helper for reliable AsyncClient
def get_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Create an AsyncClient with IPv4 preference to avoid IPv6 timeouts."""
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    return httpx.AsyncClient(transport=transport, timeout=timeout)

# Telegram HTTP Helper Functions
async def send_chat_action(chat_id: int | str, action: str = "typing"):
    try:
        async with get_http_client(timeout=10.0) as client:
            await client.post(
                f"{TELEGRAM_API_BASE}/sendChatAction",
                json={"chat_id": chat_id, "action": action}
            )
    except Exception as e:
        logger.warning(f"Failed to send chat action {action}: {e}")

async def send_telegram_message(chat_id: int | str, text: str):
    """Send text message, chunking if exceeding Telegram's 4096 character limit."""
    chunk_size = 4000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]
    
    async with get_http_client(timeout=30.0) as client:
        for chunk in chunks:
            # First try sending with Markdown formatting
            try:
                res = await client.post(
                    f"{TELEGRAM_API_BASE}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "Markdown"
                    }
                )
                if res.status_code != 200:
                    # Fallback to plain text if Markdown parsing fails
                    await client.post(
                        f"{TELEGRAM_API_BASE}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": chunk
                        }
                    )
            except Exception as e:
                logger.error(f"Error sending message chunk: {e}")

async def send_telegram_voice(chat_id: int | str, audio_bytes: bytes, caption: str = ""):
    """Send voice note back to Telegram using sendVoice."""
    try:
        files = {
            "voice": ("voice.mp3", audio_bytes, "audio/mpeg")
        }
        data = {
            "chat_id": str(chat_id)
        }
        if caption:
            data["caption"] = caption[:1024]
        
        async with get_http_client(timeout=60.0) as client:
            res = await client.post(
                f"{TELEGRAM_API_BASE}/sendVoice",
                data=data,
                files=files
            )
            if res.status_code != 200:
                logger.error(f"Failed to send voice: {res.text}")
    except Exception as e:
        logger.error(f"Error sending voice note: {e}")

async def download_telegram_file(file_id: str) -> Optional[bytes]:
    """Get file path from Telegram and download raw bytes."""
    try:
        async with get_http_client(timeout=30.0) as client:
            res = await client.get(
                f"{TELEGRAM_API_BASE}/getFile",
                params={"file_id": file_id}
            )
            data = res.json()
            if not data.get("ok"):
                logger.error(f"getFile failed: {data}")
                return None
            file_path = data["result"]["file_path"]
            file_res = await client.get(f"{TELEGRAM_FILE_BASE}/{file_path}")
            if file_res.status_code == 200:
                return file_res.content
            logger.error(f"Failed downloading file from {file_path}: {file_res.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None

async def synthesize_speech(text: str, voice: str) -> bytes:
    """Synthesize voice using Microsoft Edge TTS into MP3 bytes."""
    communicate = edge_tts.Communicate(text=text, voice=voice)
    audio_buffer = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.extend(chunk["data"])
    return bytes(audio_buffer)

# FastAPI Application
app = FastAPI(title="Khmer AI Tutor Bot API", version="1.0.0")

@app.get("/")
@app.get("/{path:path}")
async def health_check(path: str = ""):
    return {
        "status": "online",
        "service": "Khmer AI Tutor Bot",
        "model": GEMINI_MODEL,
        "runtime": "Vercel Serverless Python",
        "path": path
    }

@app.post("/")
@app.post("/{path:path}")
async def telegram_webhook(request: Request, path: str = ""):
    try:
        update = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True, "status": "no_message"}

    sender = message.get("from", {})
    user_id = sender.get("id")
    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return {"ok": True, "status": "no_chat_id"}

    # Security: Whitelist check
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt from user_id: {user_id}")
        return {"ok": True, "status": "ignored_unauthorized"}

    # Handle /start or /help commands
    text_content = message.get("text", "")
    if text_content in ["/start", "/help"]:
        welcome_text = (
            "👋 **សួស្តី! ខ្ញុំជា Khmer AI Tutor Bot (គ្រូបង្រៀន AI ខ្មែរ-អន្តរជាតិ)** 🇰🇭✨\n\n"
            "ខ្ញុំត្រៀមខ្លួនជាស្រេចដើម្បីជួយអ្នកលើការសិក្សា និងការស្រាវជ្រាវគ្រប់កម្រិត៖\n\n"
            "📚 **១. ដោះស្រាយលំហាត់ (ថ្នាក់ទី១ ដល់ មហាវិទ្យាល័យ):**\n"
            "• គណិតវិទ្យា, រូបវិទ្យា, គីមីវិទ្យា, ជីវវិទ្យា, អក្សរសាស្ត្រខ្មែរ\n"
            "• ពន្យល់ជាជំហានៗ (Step-by-step) យ៉ាងក្បោះក្បាយ\n\n"
            "🏛️ **២. ត្រៀមប្រឡងគ្រូ & ប្រឡងក្របខណ្ឌរដ្ឋ:**\n"
            "• វិញ្ញាសាចំណេះដឹងទូទៅ, គរុកោសល្យ, វប្បធម៌ទូទៅ, ច្បាប់ និងប្រវត្តិសាស្ត្រ\n"
            "• វិញ្ញាសាប្រឡងគ្រូបឋម, អនុវិទ្យាល័យ, វិទ្យាល័យ\n\n"
            "🇬🇧 **៣. រៀន និងសន្ទនាភាសាអង់គ្លេស:**\n"
            "• កែកំហុសវេយ្យាករណ៍ (Grammar Correction)\n"
            "• ដៃគូសន្ទនាផ្ទាល់ជាភាសាអង់គ្លេស (Interactive Conversation)\n\n"
            "🎙️ **វិធីសាស្ត្រប្រើប្រាស់ (Multimodal):**\n"
            "1. **Text:** វាយសំណួរ ឬលំហាត់មកកាន់ខ្ញុំ\n"
            "2. **Photo:** ថតរូបលំហាត់ពីសៀវភៅ ឬក្រដាសវិញ្ញាសាផ្ញើមក\n"
            "3. **Voice Note:** ផ្ញើសារជាសំឡេង (.ogg) ខ្ញុំនឹងស្តាប់ ឆ្លើយជាអក្សរ និងបន្លឺជាសំឡេង (Voice Reply) ត្រឡប់ទៅវិញភ្លាមៗ!\n\n"
            "💡 *សូមផ្ញើសំណួរ រូបភាព ឬសារជាសំឡេងមកបានឥឡូវនេះ!*"
        )
        await send_telegram_message(chat_id, welcome_text)
        return {"ok": True, "status": "welcomed"}

    client = get_gemini_client()

    # 1. Voice Note / Audio Processing (Voice-to-Voice)
    voice_info = message.get("voice") or message.get("audio")
    if voice_info:
        await send_chat_action(chat_id, "record_voice")
        file_id = voice_info.get("file_id")
        audio_bytes = await download_telegram_file(file_id)
        if not audio_bytes:
            await send_telegram_message(chat_id, "⚠️ មិនអាចទាញយកឯកសារសំឡេងបានទេ។ សូមព្យាយាមម្តងទៀត។")
            return {"ok": True, "status": "audio_download_failed"}

        try:
            # Pass audio directly to Gemini
            mime_type = voice_info.get("mime_type", "audio/ogg")
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            
            prompt = (
                "Please listen carefully to this student's voice recording and provide an expert, encouraging, "
                "and helpful tutoring response. Answer in the same language they spoke (Khmer or English) "
                "with clear explanations and step-by-step logic."
            )
            
            reply_text = call_gemini(contents=[audio_part, prompt])

            # Send text reply first
            await send_telegram_message(chat_id, reply_text)

            # Generate and send Voice reply using edge-tts
            tts_text = clean_text_for_tts(reply_text)
            if tts_text:
                selected_voice = KHMER_VOICE if contains_khmer(tts_text) else ENGLISH_VOICE
                voice_data = await synthesize_speech(tts_text[:2000], selected_voice)
                if voice_data:
                    await send_telegram_voice(chat_id, voice_data)

            return {"ok": True, "status": "voice_processed"}
        except Exception as e:
            logger.error(f"Error processing voice: {e}")
            await send_telegram_message(chat_id, f"⚠️ បញ្ហាក្នុងការដំណើរការសំឡេង៖ {str(e)}")
            return {"ok": True, "status": "voice_error"}

    # 2. Photo / Image Processing
    photo_list = message.get("photo")
    if photo_list:
        await send_chat_action(chat_id, "typing")
        # Largest photo is the last item
        file_id = photo_list[-1].get("file_id")
        photo_bytes = await download_telegram_file(file_id)
        if not photo_bytes:
            await send_telegram_message(chat_id, "⚠️ មិនអាចទាញយករូបភាពបានទេ។ សូមព្យាយាមម្តងទៀត។")
            return {"ok": True, "status": "photo_download_failed"}

        caption = message.get("caption", "").strip()
        photo_prompt = caption or (
            "សូមជួយវិភាគ និងដោះស្រាយលំហាត់ក្នុងរូបភាពនេះជាជំហានៗដោយក្បោះក្បាយ ច្បាស់លាស់ "
            "ព្រមទាំងបង្ហាញរូបមន្ត និងចម្លើយចុងក្រោយឱ្យបានច្បាស់។"
        )

        try:
            image_part = types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg")
            reply_text = call_gemini(contents=[image_part, photo_prompt])
            await send_telegram_message(chat_id, reply_text)
            return {"ok": True, "status": "photo_processed"}
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await send_telegram_message(chat_id, f"⚠️ បញ្ហាក្នុងការដំណើរការរូបភាព៖ {str(e)}")
            return {"ok": True, "status": "photo_error"}

    # 3. Standard Text Query Processing
    if text_content:
        await send_chat_action(chat_id, "typing")
        try:
            reply_text = call_gemini(contents=text_content)
            await send_telegram_message(chat_id, reply_text)
            return {"ok": True, "status": "text_processed"}
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            await send_telegram_message(chat_id, f"⚠️ បញ្ហាក្នុងការឆ្លើយតប៖ {str(e)}")
            return {"ok": True, "status": "text_error"}

    return {"ok": True, "status": "unsupported_media"}
