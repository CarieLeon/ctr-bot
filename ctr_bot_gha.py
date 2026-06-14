#!/usr/bin/env python3
"""CTR Bot v6 — Proxy via Playwright native API"""
import sys, json, os, time, random, asyncio, re
from datetime import datetime, timezone
from playwright.async_api import async_playwright

PROXY_URL = os.environ.get("PROXY_URL", "")

# Parse proxy
PROXY_HOST, PROXY_USER, PROXY_PASS = "", "", ""
if PROXY_URL:
    m = re.match(r'https?://(.+?):(.+?)@(.+)', PROXY_URL)
    if m:
        PROXY_USER, PROXY_PASS, PROXY_HOST = m.group(1), m.group(2), m.group(3)
    else:
        PROXY_HOST = PROXY_URL

TARGET = "agenceseo-annecy.fr"

KEYWORDS = [
    "agence seo annecy",
    "agence referencement annecy",
    "referencement site web annecy",
    "creation site internet annecy",
    "seo haute savoie",
    "referencement local google",
]

async def search_keyword(page, kw):
    result = {"keyword": kw, "success": False, "position": None}
    try:
        await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Cookies
        try:
            btn = await page.query_selector("button:has-text('Tout refuser'), button:has-text('Refuser')")
            if btn: await btn.click()
        except: pass
        
        search = await page.query_selector('textarea[name="q"]')
        if not search:
            result["error"] = "no search box"
            return result
        
        await search.click()
        await search.fill(kw)
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle", timeout=20000)
        await asyncio.sleep(1)
        
        # Check results
        title = await page.title()
        result["debug_title"] = title
        
        # Find our site
        all_links = await page.evaluate(f"""(t) => {{
            const results = [];
            document.querySelectorAll('h3').forEach((h3, i) => {{
                const a = h3.closest('a');
                const url = a ? a.href : '';
                results.push({{pos: i+1, text: h3.innerText.trim().substring(0,60), url: url.substring(0,100)}});
            }});
            return results;
        }}""")
        
        result["serp_results"] = all_links[:5]
        
        found = False
        for link_info in all_links:
            if TARGET in link_info.get("url", ""):
                result["position"] = link_info["pos"]
                found = True
                break
        
        if found:
            our_link = await page.query_selector(f'a[href*="{TARGET}"]')
            if our_link:
                await our_link.click()
                await page.wait_for_load_state("networkidle", timeout=20000)
                # Dwell time
                for _ in range(random.randint(2, 4)):
                    await page.evaluate(f'window.scrollBy(0, {random.randint(100, 400)})')
                    await asyncio.sleep(random.uniform(1, 3))
                await asyncio.sleep(random.uniform(10, 25))
                result["success"] = True
                print(f"  ✅ #{result['position']}")
            else:
                result["error"] = "found but no link"
        else:
            blocked = False
            try:
                body = await page.evaluate("document.body.innerText.substring(0,200)")
                if "captcha" in body.lower(): blocked = "captcha"
                if "unusual traffic" in body.lower(): blocked = "blocked"
            except: pass
            result["error"] = f"not found (title: {title[:40]}, blocked: {blocked or 'no'})"
            print(f"  ❌ {result['error']}")
            
    except Exception as e:
        err = str(e)[:100]
        result["error"] = err
        print(f"  ❌ {err}")
    
    return result

async def run():
    async with async_playwright() as p:
        browser_kwargs = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        }
        browser = await p.chromium.launch(**browser_kwargs)
        
        context_kwargs = {
            "locale": "fr-FR",
            "timezone_id": "Europe/Paris",
            "viewport": {"width": 1920, "height": 1080},
        }
        # Playwright native proxy (with auth)
        if PROXY_HOST:
            proxy_cfg = {"server": f"http://{PROXY_HOST}"}
            if PROXY_USER:
                proxy_cfg["username"] = PROXY_USER
                proxy_cfg["password"] = PROXY_PASS
            context_kwargs["proxy"] = proxy_cfg
            print(f"🌐 Proxy: {PROXY_HOST}")
        
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        
        # Test proxy
        try:
            await page.goto("https://api.ipify.org", wait_until="domcontentloaded", timeout=15000)
            ip = await page.evaluate("document.body.innerText")
            print(f"🌐 IP: {ip.strip()}")
        except Exception as e:
            print(f"🌐 Proxy test: {str(e)[:50]}")
        
        results = []
        for i, kw in enumerate(KEYWORDS):
            print(f"\n[{i+1}/{len(KEYWORDS)}] {kw}")
            r = await search_keyword(page, kw)
            results.append(r)
            if i < len(KEYWORDS) - 1:
                pause = random.randint(15, 40)
                print(f"    ⏳ {pause}s")
                await asyncio.sleep(pause)
        
        await browser.close()
        
        ok = sum(1 for r in results if r["success"])
        print(f"\n{'='*50}")
        print(f"RESULTS: {ok}/{len(KEYWORDS)}")
        for r in results:
            s = "✅" if r["success"] else "❌"
            p = r.get("position", r.get("error", "?"))
            print(f"  {s} {r['keyword'][:30]:30s} -> {p}")
        
        with open("/tmp/ctr_results.json", "w") as f:
            json.dump({"results": results, "time": datetime.now(timezone.utc).isoformat()}, f, indent=2, default=str)

if __name__ == "__main__":
    asyncio.run(run())
