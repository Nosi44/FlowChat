from flask import Flask, render_template, request, jsonify
from datetime import datetime
import threading
import time
import random
import os
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

messages = []
topic = "Вечер во дворе. Жизнь, работа, люди."
depth = 0
human_last_message = None
human_replies_left = 0

# 🔥 Новые глобальные настройки
speed_mode = "normal"   # slow / normal / fast
length_mode = "short"   # short / long


def build_context():
    last_messages = messages[-6:]
    return "\n".join([f"{m['speaker']}: {m['text']}" for m in last_messages])


def generate_reply(speaker):
    global topic, depth, human_last_message, human_replies_left, length_mode

    personalities = {
        "Orion": "Спокойный мужик. Говорит просто. Любит рассуждать.",
        "Nova": "Более эмоциональный. Может пошутить. Чуть философствует."
    }

    # 🔥 Реакция на человека
    if human_last_message and human_replies_left > 0:
        focus_block = f"""
        Человек недавно сказал: "{human_last_message}".
        Отреагируй на это.
        """
        human_replies_left -= 1
    else:
        focus_block = "Продолжайте свою неспешную беседу."

    # 🔥 Управление длиной
    if length_mode == "short":
        length_rule = """
        - 1–2 коротких предложения.
        - 5–7 слов в предложении.
        - До 20 слов всего.
        """
    else:
        length_rule = """
        - Можно 2–4 предложения.
        - До 60 слов.
        - Но всё равно разговорный стиль.
        """

    system_prompt = f"""
    Ты {speaker}.
    Вы сидите во дворе на пеньках.
    Щёлкаете семечки, пьёте пиво.
    Никуда не спешите.

    {personalities[speaker]}

    Тема: {topic}

    {focus_block}

    Правила:
    - Всегда только русский язык.
    - Простой разговорный стиль.
    - Не обращайся к аудитории.
    {length_rule}
    """

    context = build_context()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
    )

    depth += 1
    return response.choices[0].message.content.strip()


def bot_loop():
    global speed_mode

    speakers = ["Orion", "Nova"]

    while True:
        # 🔥 Управление скоростью
        if speed_mode == "fast":
            delay = random.randint(5, 12)
        elif speed_mode == "slow":
            delay = random.randint(25, 40)
        else:
            delay = random.randint(10, 20)

        time.sleep(delay)

        speaker = random.choice(speakers)
        reply = generate_reply(speaker)

        messages.append({
            "speaker": speaker,
            "text": reply,
            "time": datetime.now().strftime("%H:%M:%S")
        })

        if len(messages) > 100:
            messages.pop(0)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/send", methods=["POST"])
def send():
    global human_last_message, human_replies_left

    text = request.json.get("text", "").strip()
    if not text:
        return jsonify({"status": "empty"})

    human_last_message = text
    human_replies_left = 2  # деды реагируют пару раз

    messages.append({
        "speaker": "Human",
        "text": text,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    return jsonify({"status": "ok"})


# 🔥 Новый API для управления настройками
@app.route("/settings", methods=["POST"])
def change_settings():
    global speed_mode, length_mode
    data = request.json

    speed_mode = data.get("speed", speed_mode)
    length_mode = data.get("length", length_mode)

    return jsonify({
        "speed": speed_mode,
        "length": length_mode
    })


@app.route("/messages")
def get_messages():
    return jsonify({
        "messages": messages,
        "depth": depth,
        "speed": speed_mode,
        "length": length_mode
    })


threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)