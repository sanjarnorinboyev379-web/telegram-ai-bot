require("dotenv").config();
const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");
const path = require("path");

const BOT_TOKEN = process.env.BOT_TOKEN;
const GROQ_API_KEY = process.env.GROQ_API_KEY;
const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY;
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const STABILITY_API_KEY = process.env.STABILITY_API_KEY;

const bot = new TelegramBot(BOT_TOKEN, { polling: true });

const SYSTEM_PROMPT = `
Sen professional multimodal AI assistantsan.
Rasmni tahlil qilasan.
Kod screenshot bo‘lsa kodni ajrat.
Link bo‘lsa linkni chiqar.
Matn bo‘lsa OCR qil.
Rasm edit so‘ralsa image editing prompt yarat.
Faqat aniq javob ber.
`;

async function askGroq(text) {
  try {
    const res = await axios.post(
      "https://api.groq.com/openai/v1/chat/completions",
      {
        model: "llama-3.3-70b-versatile",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: text }
        ]
      },
      {
        headers: {
          Authorization: `Bearer ${GROQ_API_KEY}`
        }
      }
    );
    return res.data.choices[0].message.content;
  } catch {
    return null;
  }
}

async function askDeepseek(text) {
  try {
    const res = await axios.post(
      "https://api.deepseek.com/chat/completions",
      {
        model: "deepseek-chat",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: text }
        ]
      },
      {
        headers: {
          Authorization: `Bearer ${DEEPSEEK_API_KEY}`
        }
      }
    );
    return res.data.choices[0].message.content;
  } catch {
    return null;
  }
}

async function analyzeImageWithOpenRouter(imageUrl, userPrompt = "Bu rasmni tahlil qil") {
  try {
    const res = await axios.post(
      "https://openrouter.ai/api/v1/chat/completions",
      {
        model: "openai/gpt-4o-mini",
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: userPrompt },
              {
                type: "image_url",
                image_url: {
                  url: imageUrl
                }
              }
            ]
          }
        ]
      },
      {
        headers: {
          Authorization: `Bearer ${OPENROUTER_API_KEY}`,
          "Content-Type": "application/json"
        }
      }
    );
    return res.data.choices[0].message.content;
  } catch (e) {
    return "❌ Rasm tahlil qilib bo‘lmadi";
  }
}

async function editImage(prompt) {
  try {
    const form = new FormData();
    form.append("prompt", prompt);
    form.append("output_format", "png");

    const res = await axios.post(
      "https://api.stability.ai/v2beta/stable-image/generate/core",
      form,
      {
        headers: {
          Authorization: `Bearer ${STABILITY_API_KEY}`,
          Accept: "image/*",
          ...form.getHeaders()
        },
        responseType: "arraybuffer"
      }
    );

    return Buffer.from(res.data);
  } catch {
    return null;
  }
}

function isEditRequest(text) {
  const t = text.toLowerCase();
  return (
    t.includes("o'zgartir") ||
    t.includes("edit") ||
    t.includes("fonni olib tashla") ||
    t.includes("background remove") ||
    t.includes("rangini o'zgartir")
  );
}

bot.onText(/\/start/, async msg => {
  await bot.sendMessage(
    msg.chat.id,
    "🚀 Professional Multimodal AI Bot ishga tushdi."
  );
});

bot.on("message", async msg => {
  const chatId = msg.chat.id;

  if (msg.text && msg.text.startsWith("/start")) return;

  await bot.sendChatAction(chatId, "typing");

  if (msg.photo) {
    try {
      const photo = msg.photo[msg.photo.length - 1];
      const file = await bot.getFile(photo.file_id);
      const imageUrl = `https://api.telegram.org/file/bot${BOT_TOKEN}/${file.file_path}`;

      const caption = msg.caption || "Bu rasmni tahlil qil";

      if (isEditRequest(caption)) {
        const edited = await editImage(caption);
        if (edited) {
          await bot.sendPhoto(chatId, edited);
        } else {
          await bot.sendMessage(chatId, "❌ Rasm edit qilib bo‘lmadi");
        }
        return;
      }

      const analysis = await analyzeImageWithOpenRouter(imageUrl, caption);
      await bot.sendMessage(chatId, analysis);
      return;
    } catch {
      await bot.sendMessage(chatId, "❌ Rasmni qayta ishlashda xatolik");
      return;
    }
  }

  if (msg.text) {
    const text = msg.text;

    if (text.startsWith("http://") || text.startsWith("https://")) {
      await bot.sendMessage(chatId, `🔗 Link qabul qilindi:\n${text}`);
      return;
    }

    let reply = await askGroq(text);
    if (!reply) reply = await askDeepseek(text);
    if (!reply) reply = "❌ Javob topilmadi";

    await bot.sendMessage(chatId, reply);
  }
});

console.log("🚀 Full Professional AI Bot ishga tushdi...");