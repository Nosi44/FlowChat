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

speed_mode = "normal"
length_mode = "short"
paused = False


def build_context():
    last_messages = messages[-6:]
    return "\n".join([f"{m['speaker']}: {m['text']}" for m in last_messages])


def clean_reply(reply):
    reply = reply.strip()

    # убираем возможные префиксы
    for name in ["Orion:", "Nova:"]:
        if reply.startswith(name):
            reply = reply.replace(name, "", 1).strip()

    # если модель вдруг написала за двоих — берём только первую строку
    if "\n" in reply:
        reply = reply.split("\n")[0].strip()

    return reply


def generate_reply(speaker):
    global depth, human_last_message, human_replies_left

    personalities = {
        "Orion": "Спокойный мужик. Говорит просто. Без пафоса.",
        "Nova": "Чуть эмоциональнее. Может подшутить. Но без спектакля."
    }

    if human_last_message and human_replies_left > 0:
        chance = random.random()

        if chance > 0.3:  # 70% шанс ещё говорить по теме
            focus_block = f"""
            Человек сказал: "{human_last_message}".
            Ответь на это.
            """
            human_replies_left -= 1
        else:
            focus_block = "Плавно возвращайтесь к своей беседе."
            human_replies_left -= 1

    if length_mode == "short":
        length_rule = """
        - 1–2 коротких предложения.
        - До 20 слов всего.
        """
    else:
        length_rule = """
        - Можно 2–4 предложения.
        - До 60 слов.
        """

    system_prompt = f"""
    Ты {speaker}.
    Вы сидите во дворе на пеньках.
    Щёлкаете семечки, вокруг царит атмосфера спокойствия умиротворения, 
    чирикают птицы, ПАСУТСЯ КОРОВЫ, вдалеке поскрипывает дерево, 
    шелестит солома на крышах сельских домиков, 
    неподалеку слышно как играются дети за свинарником, 
    ведуте беседы на разные темы.
    Никуда не спешите.

    {personalities[speaker]}

    {focus_block}

    Правила:
    - Только русский язык.
    - Простой разговор.
    - Не философствуй слишком.
    - Не обращайся к аудитории.
    - Ты отвечаешь только от своего имени.
    - Никогда не пиши за другого персонажа.
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

    reply = clean_reply(response.choices[0].message.content)
    depth += 1
    return reply


def bot_loop():
    global paused

    speakers = ["Orion", "Nova"]

    while True:
        if paused:
            time.sleep(1)
            continue

        if speed_mode == "fast":
            delay = random.randint(5, 10)
        elif speed_mode == "slow":
            delay = random.randint(25, 35)
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
    
    if len(text) < 20:
        human_replies_left = random.randint(2, 5)
    else:
        human_replies_left = random.randint(5, 20)

    messages.append({
        "speaker": "Human",
        "text": text,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    return jsonify({"status": "ok"})


@app.route("/settings", methods=["POST"])
def change_settings():
    global speed_mode, length_mode, paused
    data = request.json

    speed_mode = data.get("speed", speed_mode)
    length_mode = data.get("length", length_mode)
    paused = data.get("paused", paused)

    return jsonify({
        "speed": speed_mode,
        "length": length_mode,
        "paused": paused
    })


@app.route("/messages")
def get_messages():
    return jsonify({
        "messages": messages,
        "depth": depth,
        "speed": speed_mode,
        "length": length_mode,
        "paused": paused
    })


threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)