import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:\\temp"), "chrome_cdp_ui_verify")
PORT = 9222

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self._id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=20 * 1024 * 1024)

    async def send(self, method, params=None):
        self._id += 1
        msg_id = self._id
        payload = {"id": msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            resp_str = await self.ws.recv()
            resp = json.loads(resp_str)
            if resp.get("id") == msg_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP error in {method}: {resp['error']}")
                return resp.get("result", {})

    async def evaluate(self, js_expr, await_promise=True):
        res = await self.send("Runtime.evaluate", {
            "expression": js_expr,
            "awaitPromise": await_promise,
            "returnByValue": True
        })
        val = res.get("result", {})
        if "value" in val:
            return val["value"]
        return val

    async def screenshot(self, filepath):
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        data = base64.b64decode(res["data"])
        with open(filepath, "wb") as f:
            f.write(data)
        print(f"Captured screenshot: {filepath} ({len(data)} bytes)")

    async def close(self):
        if self.ws:
            await self.ws.close()

async def main():
    # 1. Start Chrome headless with remote debugging
    print("Launching Chrome headless with CDP...")
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={PORT}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={USER_DATA_DIR}",
        "--window-size=1280,900",
        "about:blank"
    ])
    
    try:
        # Wait for port 9222
        time.sleep(2)
        json_url = f"http://127.0.0.1:{PORT}/json"
        tabs = None
        for _ in range(10):
            try:
                with urllib.request.urlopen(json_url, timeout=2) as resp:
                    tabs = json.loads(resp.read().decode())
                    break
            except Exception:
                time.sleep(0.5)

        if not tabs:
            raise RuntimeError("Failed to query Chrome targets from CDP.")

        target = [t for t in tabs if t.get("type") == "page"][0]
        ws_url = target["webSocketDebuggerUrl"]
        print(f"Connecting to CDP at {ws_url}...")

        client = CDPClient(ws_url)
        await client.connect()
        await client.send("Page.enable")
        await client.send("DOM.enable")

        artifacts_dir = r"C:\Users\naiya\.gemini\antigravity-ide\brain\b97733cd-980a-41a2-b675-bd42f627fea2"
        os.makedirs(artifacts_dir, exist_ok=True)

        # -------------------------------------------------------------------
        # Step 1: Navigate to http://127.0.0.1:8000/ui
        # -------------------------------------------------------------------
        print("Navigating to http://127.0.0.1:8000/ui...")
        await client.send("Page.navigate", {"url": "http://127.0.0.1:8000/ui"})
        await asyncio.sleep(2.5)

        # 1. Dashboard screenshot
        shot1 = os.path.join(artifacts_dir, "screenshot_1_dashboard.png")
        await client.screenshot(shot1)

        # Check navigation tabs
        nav_info = await client.evaluate("""(() => {
            const tabs = Array.from(document.querySelectorAll('.nav-tabs-bar .nav-tab')).map(t => ({
                id: t.id,
                text: t.innerText.trim(),
                selected: t.getAttribute('aria-selected')
            }));
            const chatBtn = document.getElementById('btn-open-chat');
            return {
                tabs: tabs,
                chatBtnVisible: chatBtn ? window.getComputedStyle(chatBtn).display !== 'none' : false
            };
        })()""")
        print("Navigation and Chat Button status:", json.dumps(nav_info, indent=2))

        # -------------------------------------------------------------------
        # Step 2: Open Chat Drawer and send "Why is TCS blocked?"
        # -------------------------------------------------------------------
        print("Opening chat drawer and sending question...")
        await client.evaluate("""(() => {
            const chatBtn = document.getElementById('btn-open-chat');
            if (chatBtn) chatBtn.click();
        })()""")
        await asyncio.sleep(1)

        # Type message and click send
        await client.evaluate("""(() => {
            const input = document.getElementById('chat-input-text');
            input.value = "Why is TCS blocked?";
            const form = document.getElementById('chat-input-form');
            form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        })()""")

        # Wait for assistant response to appear
        for _ in range(15):
            await asyncio.sleep(0.8)
            msg_count = await client.evaluate("document.querySelectorAll('#chat-messages-container .chat-message').length")
            if msg_count >= 3: # welcome message + user question + assistant response
                break

        chat_state = await client.evaluate("""(() => {
            const msgs = Array.from(document.querySelectorAll('#chat-messages-container .chat-message')).map(m => ({
                sender: m.classList.contains('user') ? 'user' : 'assistant',
                text: m.innerText.trim()
            }));
            const drawer = document.getElementById('chat-drawer');
            return {
                drawerOpen: drawer.classList.contains('open') || drawer.getAttribute('aria-hidden') === 'false',
                messages: msgs
            };
        })()""")
        print(f"Chat State: Drawer open={chat_state.get('drawerOpen')}, total messages={len(chat_state.get('messages', []))}")
        if chat_state.get('messages'):
            print("Latest message:", chat_state['messages'][-1]['text'][:200])

        shot2 = os.path.join(artifacts_dir, "screenshot_2_chat_drawer_tcs.png")
        await client.screenshot(shot2)

        # Close chat drawer
        await client.evaluate("""(() => {
            const closeBtn = document.getElementById('btn-close-chat');
            if (closeBtn) closeBtn.click();
        })()""")
        await asyncio.sleep(0.5)

        # -------------------------------------------------------------------
        # Step 3: Predictions Navigation, Model Dropdown Check & Prediction Explanation
        # -------------------------------------------------------------------
        print("Navigating to Predictions tab...")
        await client.evaluate("""(() => {
            const tabBtn = document.getElementById('tab-btn-predict');
            if (tabBtn) tabBtn.click();
        })()""")
        await asyncio.sleep(1)

        pred_workflow_info = await client.evaluate("""(() => {
            const modelSelect = document.getElementById('model-select');
            const accordion = document.getElementById('advanced-options-accordion');
            const symbolInput = document.getElementById('symbol-input');
            const predictBtn = document.getElementById('btn-run-prediction');
            const chips = Array.from(document.querySelectorAll('#quick-ticker-chips .chip')).map(c => ({
                symbol: c.dataset.symbol,
                badge: c.querySelector('.chip-badge') ? c.querySelector('.chip-badge').innerText : ''
            }));
            return {
                modelSelectInAccordion: accordion ? accordion.contains(modelSelect) : false,
                accordionOpen: accordion ? accordion.open : false,
                symbolInputPresent: !!symbolInput,
                predictBtnPresent: !!predictBtn,
                chips: chips
            };
        })()""")
        print("Prediction Form Diagnostics:", json.dumps(pred_workflow_info, indent=2))

        # Run Prediction for BHARTIARTL
        print("Executing prediction for BHARTIARTL...")
        await client.evaluate("""(() => {
            const input = document.getElementById('symbol-input');
            input.value = "BHARTIARTL";
            const form = document.getElementById('prediction-form');
            if (form) form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        })()""")

        # Wait for prediction result card to populate
        for _ in range(15):
            await asyncio.sleep(0.8)
            res_visible = await client.evaluate("""(() => {
                const resCard = document.getElementById('predict-results-panel');
                return resCard && window.getComputedStyle(resCard).display !== 'none';
            })()""")
            if res_visible:
                break

        pred_result_info = await client.evaluate("""(() => {
            const dirBadge = document.getElementById('res-direction-val');
            const probUp = document.getElementById('res-prob-up');
            const probDown = document.getElementById('res-prob-down');
            const modelBadge = document.getElementById('res-model-badge');
            const synthesisNarrative = document.getElementById('llm-synthesis-narrative');
            return {
                direction: dirBadge ? dirBadge.innerText.trim() : null,
                probUp: probUp ? probUp.innerText.trim() : null,
                probDown: probDown ? probDown.innerText.trim() : null,
                model: modelBadge ? modelBadge.innerText.trim() : null,
                explanation: synthesisNarrative ? synthesisNarrative.innerText.trim().slice(0, 200) : null
            };
        })()""")
        print("Prediction Result Info:", json.dumps(pred_result_info, indent=2))

        shot3 = os.path.join(artifacts_dir, "screenshot_3_predictions.png")
        await client.screenshot(shot3)

        # -------------------------------------------------------------------
        # Step 4: History Navigation & Search
        # -------------------------------------------------------------------
        print("Navigating to History tab...")
        await client.evaluate("""(() => {
            const tabBtn = document.getElementById('tab-btn-history');
            if (tabBtn) tabBtn.click();
        })()""")
        await asyncio.sleep(1.5)

        history_info = await client.evaluate("""(() => {
            const rows = document.querySelectorAll('#history-table-body tr');
            const filterInput = document.getElementById('history-symbol-filter');
            return {
                totalRows: rows.length,
                firstRowText: rows[0] ? rows[0].innerText.replace(/\\s+/g, ' ').trim() : ''
            };
        })()""")
        print("History Info:", json.dumps(history_info, indent=2))

        # Type filter 'BHARTIARTL' in history search
        await client.evaluate("""(() => {
            const filterInput = document.getElementById('history-symbol-filter');
            if (filterInput) {
                filterInput.value = "BHARTIARTL";
                filterInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        })()""")
        await asyncio.sleep(0.8)

        shot4 = os.path.join(artifacts_dir, "screenshot_4_history.png")
        await client.screenshot(shot4)

        # -------------------------------------------------------------------
        # Step 5: Market Events Navigation
        # -------------------------------------------------------------------
        print("Navigating to Market Events tab...")
        await client.evaluate("""(() => {
            const tabBtn = document.getElementById('tab-btn-events');
            if (tabBtn) tabBtn.click();
        })()""")
        await asyncio.sleep(1.2)

        events_info = await client.evaluate("""(() => {
            const cards = document.querySelectorAll('#events-list-container .event-card');
            return {
                totalEvents: cards.length,
                firstEventText: cards[0] ? cards[0].innerText.slice(0, 150).replace(/\\s+/g, ' ').trim() : ''
            };
        })()""")
        print("Market Events Info:", json.dumps(events_info, indent=2))

        shot5 = os.path.join(artifacts_dir, "screenshot_5_market_events.png")
        await client.screenshot(shot5)

        await client.close()
        print("Visual verification automated workflow complete!")

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
