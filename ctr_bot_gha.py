#!/usr/bin/env python3
"""
CTR Bot — pour GitHub Actions
Utilise Chrome (pré-installé sur Ubuntu Actions)
"""
import sys, json, os, time, random, asyncio
from datetime import datetime
from playwright.async_api import async_playwright

PROXY = os.environ.get("PROXY_URL", "http://1e1572fd7aac8eda:M8J6qCQiyeEhAwo4@res.proxy-seller.com:10000")
TARGET = "agenceseo-annecy.fr"

KEYWORDS = [
    "agence seo annecy",
    "agence referencement annecy",
    "referencement site web annecy",
    "creation site internet annecy",
    "seo haute savoie",
    "referencement local google",
    "agence web annecy",
    "audit seo annecy prix",
]

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            locale="fr-FR",
            timezone_id="Europe/Paris",
            proxy={"server": PROXY} if PROXY else None
        )
        
        results = []
        for i, kw in enumerate(KEYWORDS):
            print(f"[{i+1}/{len(KEYWORDS)}] {kw}")
            page = await context.new_page()
            result = {"keyword": kw, "success": False, "position": None}
            
            try:
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=20000)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                search = await page.query_selector('textarea[name="q"]')
                if search:
                    await search.click()
                    await search.fill(kw)
                    await page.keyboard.press("Enter")
                    await page.wait_for_selector("h3", timeout=15000)
                    await asyncio.sleep(1)
                    
                    links = await page.query_selector_all('a[href*="agenceseo-annecy"]')
                    h3s = await page.query_selector_all("h3")
                    
                    if links:
                        for j, h3 in enumerate(h3s):
                            parent = await h3.evaluate("el => el.closest('a') ? el.closest('a').href : ''")
                            if TARGET in parent:
                                result["position"] = j + 1
                                break
                        
                        await links[0].click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        await asyncio.sleep(random.uniform(10, 30))
                        result["success"] = True
                        print(f"  OK -> #{result['position']}")
                    else:
                        print(f"  Site pas trouve")
                        result["error"] = "not found"
                else:
                    result["error"] = "no search box"
                    
            except Exception as e:
                result["error"] = str(e)[:80]
                print(f"  ERR: {result['error']}")
            
            await page.close()
            results.append(result)
            
            if i < len(KEYWORDS) - 1:
                pause = random.randint(15, 45)
                await asyncio.sleep(pause)
        
        await browser.close()
        
        ok = sum(1 for r in results if r["success"])
        print(f"\n=== RESULTATS: {ok}/{len(KEYWORDS)} ===")
        for r in results:
            s = "+" if r["success"] else "-"
            print(f"  {s} {r['keyword'][:30]} -> {r.get('position', r.get('error','?'))}")
        
        return results

if __name__ == "__main__":
    results = asyncio.run(run())
    summary_path = "/tmp/ctr_results.json"
    with open(summary_path, "w") as f:
        json.dump({"results": results, "time": datetime.utcnow().isoformat()}, f, indent=2, default=str)
