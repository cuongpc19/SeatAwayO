from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.type.upper() + " " + m.text))
    pg.goto("http://127.0.0.1:8080/level_player.html")
    pg.wait_for_timeout(4000)
    print("ready =", pg.evaluate("typeof ready !== 'undefined' ? ready : 'undefined'"))
    for e in errs[:12]: print(e[:400])
    br.close()
