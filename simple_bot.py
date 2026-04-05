import os
import json
import time
import urllib.parse
import urllib.request
import urllib.error

# =====================
# CONFIG
# =====================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN পাওয়া যায়নি")

ADMIN_USERNAMES = ["mehedi_chowdhury", "smmehedichowdury"]   # @ ছাড়া

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# =====================
# MEMORY STORAGE
# =====================
users = set()
blocked = set()
admin_ids = set()
reply_map = {}

# =====================
# TELEGRAM API
# =====================
def api(method, data=None):
    if data is None:
        data = {}

    url = f"{BASE_URL}/{method}"
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            print("HTTP Error:", e.read().decode("utf-8", errors="ignore"))
        except Exception:
            print("HTTP Error")
    except Exception as e:
        print("Error:", e)

    return None


def send(chat_id, text, reply_to_message_id=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_to_message_id is not None:
        data["reply_to_message_id"] = reply_to_message_id

    return api("sendMessage", data)


def typing(chat_id):
    api("sendChatAction", {"chat_id": chat_id, "action": "typing"})


def get_updates(offset=None):
    data = {"timeout": 30}
    if offset is not None:
        data["offset"] = offset
    return api("getUpdates", data)

# =====================
# HELPERS
# =====================
def is_admin(user):
    username = (user.get("username") or "").lower()
    return username in [x.lower() for x in ADMIN_USERNAMES]

# =====================
# USER HANDLER
# =====================
def handle_user(msg):
    uid = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    users.add(uid)

    if uid in blocked:
        return

    # /start দিলে কিছুই আসবে না
    if text.startswith("/start"):
        return

    typing(uid)
    time.sleep(1)

    admin_text = (
        "📩 New User Message\n"
        "User ID: " + str(uid) + "\n"
        "Message:\n" + text
    )

    for admin_id in admin_ids:
        result = send(admin_id, admin_text)
        if result and result.get("ok"):
            msg_id = result["result"]["message_id"]
            reply_map[msg_id] = uid

# =====================
# ADMIN HANDLER
# =====================
def handle_admin(msg):
    uid = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    admin_ids.add(uid)
    users.add(uid)

    if text == "/start":
        send(
            uid,
            "✅ Admin Panel\n\n"
            "/broadcast message\n"
            "/block user_id\n"
            "/unblock user_id\n\n"
            "Reply দিয়ে user-কে উত্তর দাও"
        )
        return

    if text.startswith("/broadcast "):
        msg_text = text.replace("/broadcast ", "", 1).strip()
        if not msg_text:
            send(uid, "লিখো:\n/broadcast message")
            return

        count = 0
        for u in users:
            if u not in blocked and u not in admin_ids:
                result = send(u, msg_text)
                if result and result.get("ok"):
                    count += 1

        send(uid, "Sent: " + str(count))
        return

    if text.startswith("/block "):
        try:
            target = int(text.split()[1])
            blocked.add(target)
            send(uid, "Blocked")
        except Exception:
            send(uid, "Error")
        return

    if text.startswith("/unblock "):
        try:
            target = int(text.split()[1])
            blocked.discard(target)
            send(uid, "Unblocked")
        except Exception:
            send(uid, "Error")
        return

    # Reply-to-message system
    reply = msg.get("reply_to_message")
    if reply:
        msg_id = reply.get("message_id")

        if msg_id in reply_map:
            target = reply_map[msg_id]

            if target in blocked:
                send(uid, "User blocked")
                return

            typing(target)
            time.sleep(1)
            send(target, text)

            send(uid, "Reply sent", msg["message_id"])
            return

# =====================
# MAIN LOOP
# =====================
def run():
    offset = None
    print("Bot running...")

    while True:
        data = get_updates(offset)

        if data and data.get("ok"):
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1

                if "message" in upd:
                    msg = upd["message"]

                    if msg["chat"]["type"] != "private":
                        continue

                    if is_admin(msg["from"]):
                        handle_admin(msg)
                    else:
                        handle_user(msg)

        time.sleep(1)

run()
