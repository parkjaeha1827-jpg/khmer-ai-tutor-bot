import os
import asyncio
import io
import sys
from dotenv import load_dotenv

load_dotenv()

async def run_tests():
    print("=" * 60)
    print("🚀 Khmer AI Tutor Bot - Local Integration Test Suite")
    print("=" * 60)

    # 1. Environment Variable Check
    print("\n[1/4] Checking Environment Variables...")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    allowed_user = os.getenv("ALLOWED_USER_ID", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    missing = []
    if not bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not gemini_key:
        missing.append("GEMINI_API_KEY")
    if not allowed_user:
        missing.append("ALLOWED_USER_ID")

    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("   Please make sure your .env file is configured.")
        return False
    else:
        print("✅ Environment variables loaded successfully.")
        print(f"   - Model: {gemini_model}")
        print(f"   - Allowed User ID: {allowed_user}")

    # 2. Telegram Bot API Connectivity Check
    print("\n[2/4] Testing Telegram Bot API Connectivity...")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"https://api.telegram.org/bot{bot_token}/getMe")
            data = res.json()
            if data.get("ok"):
                bot_user = data["result"]
                print(f"✅ Telegram Bot Connected: @{bot_user.get('username')} ({bot_user.get('first_name')})")
            else:
                print(f"❌ Telegram API Error: {data.get('description')}")
                return False
    except Exception as e:
        print(f"❌ Failed to reach Telegram API: {e}")
        return False

    # 3. Google GenAI (gemini-2.5-flash) Test
    print(f"\n[3/4] Testing Google GenAI ({gemini_model})...")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=gemini_key)
        
        test_prompt = "ដោះស្រាយសមីការ 2x + 10 = 20 រួចរកតម្លៃ x ជាជំហានៗ"
        print(f"   Sending query to Gemini: '{test_prompt}'...")
        response = client.models.generate_content(
            model=gemini_model,
            contents=test_prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert Cambodian tutor. Provide short, step-by-step solutions in Khmer.",
                temperature=0.7,
            )
        )
        print("✅ Gemini Response received:")
        print("-" * 40)
        print(response.text[:300] + ("..." if len(response.text) > 300 else ""))
        print("-" * 40)
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return False

    # 4. Edge-TTS Audio Generation Test
    print("\n[4/4] Testing Edge-TTS Speech Synthesis (Khmer & English)...")
    try:
        import edge_tts
        os.makedirs("test_output", exist_ok=True)

        # Test Khmer Voice
        khmer_voice = os.getenv("KHMER_VOICE", "km-KH-PisethNeural")
        khmer_text = "សួស្តី! ខ្ញុំជាគ្រូបង្រៀន AI ខ្មែរ-អន្តរជាតិ។ តើខ្ញុំអាចជួយដោះស្រាយលំហាត់អ្វីដល់អ្នក?"
        print(f"   Synthesizing Khmer voice ({khmer_voice})...")
        communicate_km = edge_tts.Communicate(text=khmer_text, voice=khmer_voice)
        km_audio = bytearray()
        async for chunk in communicate_km.stream():
            if chunk["type"] == "audio":
                km_audio.extend(chunk["data"])
        
        with open("test_output/test_khmer.mp3", "wb") as f:
            f.write(km_audio)
        print(f"✅ Khmer TTS generated successfully: test_output/test_khmer.mp3 ({len(km_audio)} bytes)")

        # Test English Voice
        eng_voice = os.getenv("ENGLISH_VOICE", "en-US-AriaNeural")
        eng_text = "Hello! I am your AI English conversation partner. How are you doing today?"
        print(f"   Synthesizing English voice ({eng_voice})...")
        communicate_en = edge_tts.Communicate(text=eng_text, voice=eng_voice)
        en_audio = bytearray()
        async for chunk in communicate_en.stream():
            if chunk["type"] == "audio":
                en_audio.extend(chunk["data"])

        with open("test_output/test_english.mp3", "wb") as f:
            f.write(en_audio)
        print(f"✅ English TTS generated successfully: test_output/test_english.mp3 ({len(en_audio)} bytes)")
    except Exception as e:
        print(f"❌ Edge-TTS Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 ALL LOCAL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
