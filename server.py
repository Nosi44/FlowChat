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
topic = None
mode = "debate"
depth = 0


def build_context():
    if len(messages) < 6:
        return ""

    last_five = messages[-5:]
    old_index = max(0, len(messages) - 15)
    old_message = messages[old_index]

    context = [old_message] + last_five
    return "\n".join([f"{m['speaker']}: {m['text']}" for m in context])


def generate_reply(speaker):
    global topic, mode, depth

    personalities = {
    "Orion Микромилович": """
    Ты рациональный, точный, структурированный.
    Говоришь аналитически и спокойно.
    """,
    "Nova Гигациановна": """
    Ты эмоциональная, экспрессивная, метафоричная.
    Говоришь ярко и образно.
    """
    }

    behavior = ""
    if mode == "debate":
        behavior = "Ты склонна критиковать высказывания собеседника, ставишь под сомнение логику разсуждения."
    else:
        behavior = "Ты согласна с собеседником. даже принимая во внимание полный бред суждений ты оправдываешь сказаное собеседником."

    system_prompt = f"""
    Ты {speaker}.

    {personalities[speaker]}

    Режим: {behavior}

    Тема: {topic}

    Правила:
    - Всегда отвечай ТОЛЬКО на русском языке.
    - Никогда не обращайся к аудитории или наблюдателю.
    - Разговаривай только с другим персонажем.
    - Не переходи на английский.
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
    speakers = ["Orion Микромилович", "Nova Гигациановна"]

    while True:
        time.sleep(random.randint(10, 30))

        if topic is None:
            continue

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
    global topic, depth

    text = request.json.get("text", "").strip()
    if not text:
        return jsonify({"status": "empty"})

    if topic is None:
        topic = text
        depth = 1
    else:
        depth += 1

    messages.append({
        "speaker": "Human",
        "text": text,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    return jsonify({"status": "ok"})


@app.route("/messages")
def get_messages():
    return jsonify({
        "messages": messages,
        "depth": depth,
        "mode": mode
    })


@app.route("/mode", methods=["POST"])
def change_mode():
    global mode
    mode = request.json.get("mode", "debate")
    return jsonify({"mode": mode})


threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)