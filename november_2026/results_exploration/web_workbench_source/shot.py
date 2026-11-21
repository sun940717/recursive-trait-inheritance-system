import sys, json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    for name, vp in (("desktop", {"width": 1320, "height": 900}), ("phone", {"width": 400, "height": 800})):
        pg = b.new_page(viewport=vp)
        logs = []
        pg.on("console", lambda m: logs.append(m.type + ": " + m.text))
        pg.on("pageerror", lambda e: logs.append("PAGEERROR: " + str(e)))
        pg.route("**/three.min.js", lambda r: r.fulfill(path="/tmp/threepkg/node_modules/three/build/three.min.js", content_type="application/javascript"))
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.goto("file:///home/claude/web/index.html")
        pg.wait_for_timeout(2500)
        if name == "desktop":
            print("three loaded:", pg.evaluate("typeof THREE"), "| stats:", pg.evaluate("JSON.stringify(window.__bench.state.lastReport)"))
            print("canvas visible:", pg.evaluate("getComputedStyle(document.getElementById('canvas')).display"), "| hscroll:", pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
            pg.screenshot(path="/home/claude/web/shot_desktop.png", full_page=False)
            # interact: flip a gene, roll mutation, skeleton view
            pg.click("#genes .chip >> nth=0"); pg.click("#btnMutate"); pg.click("#btnMutate"); pg.check("#optSkel")
            pg.wait_for_timeout(1500)
            print("after interaction:", pg.evaluate("JSON.stringify({ops: window.__bench.state.ops.length, rep: window.__bench.state.lastReport})"))
            pg.click("#btnKeep"); pg.wait_for_timeout(300)
            print("roster:", pg.evaluate("window.__bench.state.roster.map(r => r.label).join(' | ')"), "| msg:", pg.inner_text("#msg"))
            pg.screenshot(path="/home/claude/web/shot_desktop2.png", full_page=True)
        else:
            print("phone hscroll:", pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
            pg.screenshot(path="/home/claude/web/shot_phone.png", full_page=False)
        print(name, "logs:", logs[:6])
    b.close()
