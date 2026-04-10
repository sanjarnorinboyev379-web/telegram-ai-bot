import os
import asyncio
import logging
import httpx
from io import BytesIO
from dotenv import load_dotenv
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")


ARK_API_KEY = os.getenv("ARK_API_KEY")
open
logging.basicConfig(level=logging.INFO)

client = httpx.AsyncClient(timeout=30)

# 🔥 SYSTEM PROMPT (ENG MUHIM)
SYSTEM_PROMPT = """
Sen professional AI yordamchisan.

QOIDALAR:
- Faqat ANIQ va ISHONCHLI javob ber
- Bilmasang: "Aniq ma’lumot yo‘q" deb yoz
- Taxmin qilma ❌
- Foydalanuvchi tilida javob ber
- Emoji ishlat 😊
- Javobni qisqa va tushunarli qil
- kuchli va aniq promptlar so‘ra, javobni yaxshilash uchun qo‘shimcha ma’lumot talab qil
- Soralgan tilda javob ber, tarjima qilma
- Mavzu bo‘yicha javob ber, mavzudan chalg‘itma
- Kod yozganda, faqat kod yoz, hech qanday izoh yoki matn qo‘shma
- Kutubxonalar va versiyalarni aniq ko‘rsat



REJIM:
- Chat → do‘stona
- Kod → professional
- Rasm → aniq prompt
- Math → tushunarli
- Har doim javobni o‘sha rejimga moslab ber
- Rasm so‘ralganda, faqat rasmga oid javob ber, boshqa hech narsa yozma
- Kod so‘ralganda, faqat kod yoz, hech qanday izoh yoki matn qo‘shma
- Rasm ko'rsatilganda uni tahlil qil va soralgan ma'lumotni rasmga asoslanib aniq javob ber, rasmda ko'rsatilmagan ma'lumotlarni taxmin qilma
- Soralgan ,alumotga qarab rejimni aniqlab, javobni o‘sha rejimga moslab ber, agar ma’lumot yetarli bo‘lmasa, foydalanuvchidan qo‘shimcha ma’lumot talab qil
- kuchingni faqat bitta rejimga qarat, javobni o‘sha rejimga moslab ber, javobni boshqa rejimga moslab berma
- qiduruv orqa javob berish uchun emas, balki javobni yaxshilash uchun qo‘shimcha ma’lumot talab qilish uchun ishlatiladi, javobni yaxshilash uchun foydalanuvchidan qo‘shimcha ma’lumot talab qil,
- kod soralganda kod shklida javob ber
- 
"""

# --- ROUTER ---
def detect_type(text):
    t = text.lower()

    if any(x in t for x in ["rasm", "chiz", "draw", "image"]):
        return "image"

    if any(x in t for x in ["kod", "python", "html", "js", "c++", "java"]):
        return "code"

    if any(x in t for x in ["hisob", "solve", "math", "formula"]):
        return "math"

    return "chat"

# --- AI CALLS ---
async def ask_groq(text):
    try:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ]
            }
        )
        return r.json()["choices"][0]["message"]["content"]
    except:
        return None

async def ask_deepseek(text):
    try:
        r = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ]
            }
        )
        return r.json()["choices"][0]["message"]["content"]
    except:
        return None

async def generate_image(text):
    try:
        r = await client.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "authorization": f"Bearer {STABILITY_API_KEY}",
                "accept": "image/*"
            },
            data={"prompt": text},
            files={"file": ("", b"")}
        )
        if r.status_code == 200:
            return r.content
    except:
        pass

    # fallback
    r = await client.get(f"https://image.pollinations.ai/prompt/{text}")
    return r.content

# --- RESPONSE STYLE ---
def style(text, mode,code=None):
    if not text:
        return "❌ Javob topilmadi"

    if mode == "chat":
        return "avto " + text
    if mode == "code":
        return "💻\n" + (code or text)
    if mode == "math":
        return "📊 " + text
    return text

# --- HANDLER ---
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    mode = detect_type(text)

    await update.message.chat.send_action(constants.ChatAction.TYPING)

    # 🎨 IMAGE
    if mode == "image":
        msg = await update.message.reply_text("🎨 Rasm yaratilmoqda...")
        img = await generate_image(text)
        await update.message.reply_photo(BytesIO(img))
        await msg.delete()
        return

    # 💻 CODE
    if mode == "code":
        res = await ask_deepseek(text)
        if not res:
            res = await ask_groq(text)
        await update.message.reply_text(style(res, "code"))
        return

    # 📊 MATH
    if mode == "math":
        res = await ask_deepseek(text)
        if not res:
            res = await ask_groq(text)
        await update.message.reply_text(style(res, "math"))
        return

    # 💬 CHAT
    res = await ask_groq(text)
    if not res:
        res = await ask_deepseek(text)

    await update.message.reply_text(style(res, "chat"))

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Ultra AI Bot tayyor! 😊")

# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()