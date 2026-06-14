#!/usr/bin/env python3
"""CTR Bot v5 — Debug + robuste"""
import sys, json, os, time, random, asyncio
from datetime import datetime, timezone
from playwright.async_api import async_playwright

PROXY_URL = os.environ.get("PROXY_URL", "")
PROXY_USER = os.environ.get("PROXY_USER", "")
PROXY_PASS = os.environ.get("PROXY_PASS", "")

# Parse proxy URL
import re
if PROXY_URL and not PROXY_USER:
    m = re.match(r'https?://(.+?):(.+?)@(.+)', PROXY_URL)
    if m:
        PROXY_USER, PROXY_PASS, PROXY_HOST = m.groups()
        PROXY_SERVER = f"http://{PROXY_HOST}"
    else:
        PROXY_SERVER = PROXY_URL
elif PROXY_URL:
    PROXY_SERVER = PROXY_URL
else:
    PROXY_SERVER = ""

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
    result = {"keyword": kw, "success": False, "position": None, "debug": {}}
    
    try:
        # Google home
        await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(0.5, 1))
        
        # Cookies
        try:
            btn = await page.query_selector("button:has-text('Tout refuser'), button:has-text('Refuser')")
            if btn: await btn.click()
        except: pass
        
        await asyncio.sleep(0.5)
        
        # Search
        search = await page.query_selector('textarea[name="q"]')
        if not search:
            result["debug"]["error"] = "no search box"
            return result
        
        await search.click()
        await search.fill(kw)
        await page.keyboard.press("Enter")
        
        # Wait for results to load
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(1)
        
        # DEBUG: Log page info
        title = await page.title()
        url = page.url
        result["debug"]["title"] = title
        result["debug"]["url"] = url
        
        # Check for captcha/block
        body_text = await page.evaluate("document.body.innerText")
        if "captcha" in body_text.lower()[:500]:
            result["debug"]["blocked"] = "captcha"
            return result
        if "unusual traffic" in body_text.lower()[:500]:
            result["debug"]["blocked"] = "unusual traffic"
            return result
        
        # Get all result links and text
        all_results = await page.evaluate("""() => {
            const items = [];
            // Method 1: Look for all h3 inside search results
            document.querySelectorAll('h3').forEach((h3, i) => {
                const link = h3.closest('a');
                const parent = h3.closest('div[data-hveid], div.g');
                items.push({
                    type: 'h3',
                    index: i,
                    text: h3.innerText.trim(),
                    href: link ? link.href : '',
                    parentClass: parent ? parent.className : ''
                });
            });
            // Method 2: Look for all search result links
            document.querySelectorAll('a[href*="agenceseo"], a[href*="annecy"]').forEach((a) => {
                items.push({
                    type: 'link_match',
                    href: a.href,
                    text: a.innerText.trim().substring(0,80)
                });
            });
            return items;
        }""")
        
        result["debug"]["results"] = all_results[:20]
        
        # Find our site
        found = False
        for item in all_results:
            if item["type"] == "h3" and TARGET in item.get("href", ""):
                result["position"] = item["index"] + 1
                found = True
                break
            if TARGET in item.get("href", ""):
                result["position"] = "found"
                found = True
                break
        
        # If found, click and simulate visit
        if found:
            our_link = await page.query_selector(f'a[href*="{TARGET}"]')
            if our_link:
                await our_link.click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(random.uniform(15, 30))
                result["success"] = True
                result["debug"]["visited"] = True
                print(f"  ✅ Position #{result['position']}")
            else:
                result["debug"]["click_error"] = "link not found after detection"
                print(f"  ⚠️ Found in results but link not clickable")
        else:
            # Show what WAS found
            top5 = [r for r in all_results if r["type"] == "h3"][:5]
            if top5:
                result["debug"]["serp_top"] = [r["text"][:50] for r in top5]
                print(f"  ❌ Site pas trouve. Top 5: {[r['text'][:30] for r in top5]}")
            else:
                result["debug"]["serp_empty"] = True
                print(f"  ❌ Aucun résultat h3 trouvé sur Google")
    
    except Exception as e:
        result["debug"]["exception"] = str(e)[:100]
        print(f"  ❌ Erreur: {str(e)[:80]}")
    
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
        if PROXY_SERVER:
            proxy_config = {"server": PROXY_SERVER}
            if PROXY_USER:
                proxy_config["username"] = PROXY_USER
                proxy_config["password"] = PROXY_PASS
            context_kwargs["proxy"] = proxy_config
        
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        
        # Test proxy
        try:
            await page.goto("https://api.ipify.org", wait_until="domcontentloaded", timeout=15000)
            ip = await page.evaluate("document.body.innerText")
            print(f"🌐 Proxy IP: {ip.strip()}")
            result["debug"] = {"proxy_ip": ip.strip()}
        except:
            print("🌐 Proxy: OK")
        
        results = []
        for i, kw in enumerate(KEYWORDS):
            print(f"\n[{i+1}/{len(KEYWORDS)}] {kw}")
            r = await search_keyword(page, kw)
            results.append(r)
            
            if i < len(KEYWORDS) - 1:
                pause = random.randint(15, 45)
                print(f"    ⏳ pause {pause}s...")
                await asyncio.sleep(pause)
        
        await browser.close()
        
        ok = sum(1 for r in results if r["success"])
        print(f"\n{'='*50}")
        print(f"RESULTS: {ok}/{len(KEYWORDS)}")
        for r in results:
            s = "✅" if r["success"] else "❌"
            debug_info = r.get("debug", {})
            blocked = debug_info.get("blocked", "")
            pos = r.get("position", f"({r.get('error','?')})")
            print(f"  {s} {r['keyword'][:30]:30s} -> {pos} {blocked}")
        
        summary_path = "/tmp/ctr_results.json"
        with open(summary_path, "w") as f:
            json.dump({"results": results, "time": datetime.now(timezone.utc).isoformat()}, f, indent=2, default=str)

if __name__ == "__main__":
    asyncio.run(run())
