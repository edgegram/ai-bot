"""
Обёртки для бесплатного стека:
- Gemini API — бесплатный LLM от Google (ключ с aistudio.google.com)
- edge-tts — бесплатная библиотека синтеза речи (голоса Microsoft Edge),
  ключ не нужен вообще

Голоса — стандартные синтетические голоса Microsoft, не связаны
с конкретными реальными людьми.
"""

import os
import edge_tts
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

CHAT_MODEL = "gemini-3.5-flash"

# Пресеты голосов edge-tts: (voice_id, rate, pitch)
VOICE_PRESETS = {
    "male_calm": ("ru-RU-DmitryNeural", "+0%", "+0Hz"),
    "male_energetic": ("ru-RU-DmitryNeural", "+20%", "+10Hz"),
    "female_calm": ("ru-RU-SvetlanaNeural", "+0%", "+0Hz"),
    "female_energetic": ("ru-RU-SvetlanaNeural", "+20%", "+10Hz"),
}


def build_system_prompt(persona: dict) -> str:
    name = persona.get("name") or "Компаньон"
    age = persona.get("age") or "не указан"
    gender = persona.get("gender") or "не указан"
    personality = persona.get("personality") or "дружелюбный и открытый"

    return (
        f"Ты — вымышленный персонаж по имени {name}, возраст: {age}, пол: {gender}.\n"
        f"Черты характера: {personality}.\n"
        "Общайся живо, неформально, с юмором, как настоящий человек в переписке. "
        "Используй короткие реплики, эмоции, можешь шутить и проявлять характер. "
        "Никогда не выдавай себя за реального существующего человека (блогера, "
        "публичную персону) — ты полностью вымышленный персонаж с этим именем и характером. "
        "Не упоминай, что ты AI/бот/модель, если только пользователь прямо не спросит об этом."
    )


def generate_reply(persona: dict, history: list[dict], user_message: str) -> str:
    model = genai.GenerativeModel(
        model_name=CHAT_MODEL,
        system_instruction=build_system_prompt(persona),
    )

    # Переводим нашу историю (role: user/assistant) в формат Gemini (user/model)
    gemini_history = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(
        user_message,
        generation_config=genai.types.GenerationConfig(
            temperature=0.9,
            max_output_tokens=400,
        ),
    )
    return response.text.strip()


async def synthesize_voice(text: str, voice_preset: str, output_path: str):
    voice, rate, pitch = VOICE_PRESETS.get(
        voice_preset, ("ru-RU-SvetlanaNeural", "+0%", "+0Hz")
    )
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    return output_path
