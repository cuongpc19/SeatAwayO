from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for mode in ("light", "dark"):
        pg = br.new_page(viewport={"width": 1000, "height": 1100}, color_scheme=mode)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:8080/BACKGROUND_PROMPTS.html")
        pg.wait_for_timeout(1200)
        pg.screenshot(path="doc_%s.png" % mode)
        if mode == "light":
            pg.click(".copy")
            pg.wait_for_timeout(300)
            print("copy button after click:", pg.locator(".copy").first.inner_text())
            print("horizontal overflow:",
                  pg.evaluate("document.documentElement.scrollWidth > window.innerWidth"))
        print(mode, "errors:", errs[:3] or "none")
        pg.close()
    br.close()
