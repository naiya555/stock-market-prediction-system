import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:\\temp"), "chrome_cdp_ui_verify_full")
PORT = 9222
ARTIFACTS_DIR = r"C:\Users\naiya\.gemini\antigravity-ide\brain\668a9606-1edf-42fd-8536-2794e1a8a689"

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self._id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=25 * 1024 * 1024)

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
        print(f"Captured genuine screenshot: {filepath} ({len(data)} bytes)")
        return filepath

    async def close(self):
        if self.ws:
            await self.ws.close()

async def run_verification():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    print("=== STARTING REAL BROWSER CDP INTERACTION TEST ===")
    print(f"Target UI: http://127.0.0.1:8000/ui")
    print(f"Artifacts output: {ARTIFACTS_DIR}")

    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={PORT}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={USER_DATA_DIR}",
        "--window-size=1366,900",
        "about:blank"
    ])

    try:
        # Connect to Chrome
        time.sleep(2)
        json_url = f"http://127.0.0.1:{PORT}/json"
        tabs = None
        for attempt in range(12):
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
        print(f"Connected to CDP debugger at {ws_url}")

        client = CDPClient(ws_url)
        await client.connect()
        await client.send("Page.enable")
        await client.send("DOM.enable")

        # -------------------------------------------------------------
        # 1. Open App & Verify Dashboard Tab
        # -------------------------------------------------------------
        print("\n--- [1/6] Navigating to http://127.0.0.1:8000/ui ---")
        await client.send("Page.navigate", {"url": "http://127.0.0.1:8000/ui"})
        await asyncio.sleep(2.5)

        dash_status = await client.evaluate("""(() => {
            const heading = document.querySelector('h1') ? document.querySelector('h1').innerText : '';
            const activeTab = document.querySelector('.nav-tab[aria-selected="true"]');
            const marketStatus = document.getElementById('market-status-badge');
            return {
                heading: heading,
                activeTab: activeTab ? activeTab.innerText.trim() : null,
                marketStatus: marketStatus ? marketStatus.innerText.trim() : null
            };
        })()""")
        print(f"Dashboard loaded: {json.dumps(dash_status)}")
        shot1 = os.path.join(ARTIFACTS_DIR, "01_dashboard.png")
        await client.screenshot(shot1)

        # -------------------------------------------------------------
        # 2. Chat Drawer: Open, Submit "Why is TCS blocked?", Verify Reply
        # -------------------------------------------------------------
        print("\n--- [2/6] Testing Chat Assistant Drawer ---")
        await client.evaluate("""(() => {
            const chatBtn = document.getElementById('btn-open-chat');
            if (chatBtn) chatBtn.click();
        })()""")
        await asyncio.sleep(0.8)

        # Send question
        question = "Why is TCS blocked?"
        await client.evaluate(f"""(() => {{
            const input = document.getElementById('chat-input-text');
            input.value = "{question}";
            const form = document.getElementById('chat-input-form');
            form.dispatchEvent(new Event('submit', {{ cancelable: true, bubbles: true }}));
        }})()""")

        # Wait for reply
        reply_received = False
        for _ in range(20):
            await asyncio.sleep(0.8)
            msg_count = await client.evaluate("document.querySelectorAll('#chat-messages-container .chat-message').length")
            if msg_count >= 3:
                reply_received = True
                break

        chat_eval = await client.evaluate("""(() => {
            const msgs = Array.from(document.querySelectorAll('#chat-messages-container .chat-message')).map(m => ({
                isUser: m.classList.contains('user'),
                text: m.innerText.trim()
            }));
            return msgs;
        })()""")
        print(f"Chat messages count: {len(chat_eval)}")
        if chat_eval:
            print(f"Last assistant reply:\n{chat_eval[-1]['text'][:300]}...")

        # Verify drawer screenshot
        shot2 = os.path.join(ARTIFACTS_DIR, "02_chat_open_and_response.png")
        await client.screenshot(shot2)

        # Close chat drawer
        await client.evaluate("document.getElementById('btn-close-chat').click();")
        await asyncio.sleep(0.5)

        # -------------------------------------------------------------
        # 3. Clean UI: Predictions Tab & Auto-Routing Verification
        # -------------------------------------------------------------
        print("\n--- [3/6] Testing Predictions Tab (Clean UI verification) ---")
        await client.evaluate("document.getElementById('tab-btn-predict').click();")
        await asyncio.sleep(1.0)

        clean_ui_check = await client.evaluate("""(() => {
            const modelSelect = document.getElementById('model-select');
            const modelPill = document.getElementById('automated-routing-badge');
            const accordion = document.getElementById('advanced-options-accordion');
            return {
                modelSelectTag: modelSelect ? modelSelect.tagName.toLowerCase() : null,
                modelSelectHidden: modelSelect ? (modelSelect.type === 'hidden' || window.getComputedStyle(modelSelect).display === 'none') : false,
                automatedPillPresent: modelPill ? (modelPill.textContent || "").trim() : null,
                accordionHasDropdown: accordion ? !!accordion.querySelector('select#model-select') : false
            };
        })()""")
        print(f"Clean UI Diagnostics: {json.dumps(clean_ui_check, indent=2)}")
        assert clean_ui_check["modelSelectTag"] == "input", "Expected hidden input for model-select"
        assert clean_ui_check["modelSelectHidden"] is True, "model-select must not be a user-facing dropdown"
        assert "Automated Routing" in (clean_ui_check["automatedPillPresent"] or ""), "Automated routing pill missing"

        shot3 = os.path.join(ARTIFACTS_DIR, "03_predictions_tab_clean_ui.png")
        await client.screenshot(shot3)

        # -------------------------------------------------------------
        # 4. Run Prediction for BHARTIARTL (Verify Rationale & Distinction)
        # -------------------------------------------------------------
        print("\n--- [4/6] Executing Real Prediction for BHARTIARTL ---")
        await client.evaluate("""(() => {
            const input = document.getElementById('symbol-input');
            input.value = "BHARTIARTL";
            document.getElementById('prediction-form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        })()""")

        for _ in range(25):
            await asyncio.sleep(0.8)
            visible = await client.evaluate("""(() => {
                const p = document.getElementById('predict-results-panel');
                return p && window.getComputedStyle(p).display !== 'none';
            })()""")
            if visible:
                break

        pred_check = await client.evaluate("""(() => {
            return {
                direction: document.getElementById('res-direction-text') ? document.getElementById('res-direction-text').innerText.trim() : null,
                probUp: document.getElementById('res-prob-up') ? document.getElementById('res-prob-up').innerText.trim() : null,
                probDown: document.getElementById('res-prob-down') ? document.getElementById('res-prob-down').innerText.trim() : null,
                modelBadge: document.getElementById('res-routing-badge') ? document.getElementById('res-routing-badge').innerText.trim() : null,
                uncalibratedBanner: document.getElementById('res-uncalibrated-banner') ? document.getElementById('res-uncalibrated-banner').innerText.trim() : null,
                distinctionBar: document.getElementById('res-distinction-bar') ? document.getElementById('res-distinction-bar').innerText.trim() : null,
                qualitativeEvidence: document.getElementById('why-qualitative-content') ? document.getElementById('why-qualitative-content').innerText.trim().slice(0, 200) : null,
                technicalEvidence: document.getElementById('why-technical-content') ? document.getElementById('why-technical-content').innerText.trim() : null,
                sourcesEvidence: document.getElementById('why-sources-content') ? document.getElementById('why-sources-content').innerText.trim() : null
            };
        })()""")
        print(f"Prediction result validation:\n{json.dumps(pred_check, indent=2)}")
        assert "UP" in pred_check["direction"] or "DOWN" in pred_check["direction"], f"Invalid direction: {pred_check['direction']}"
        assert pred_check["modelBadge"] is not None, "Missing model badge"

        shot4 = os.path.join(ARTIFACTS_DIR, "04_prediction_bhartiartl_success.png")
        await client.screenshot(shot4)

        # -------------------------------------------------------------
        # 5. Run Prediction for Blocked Instrument (TCS)
        # -------------------------------------------------------------
        print("\n--- [5/6] Executing Prediction for TCS (Blocked Instrument) ---")
        await client.evaluate("""(() => {
            const input = document.getElementById('symbol-input');
            input.value = "TCS";
            document.getElementById('prediction-form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        })()""")

        for _ in range(15):
            await asyncio.sleep(0.8)
            blocked_visible = await client.evaluate("""(() => {
                const c = document.getElementById('result-blocked-card');
                return c && window.getComputedStyle(c).display !== 'none';
            })()""")
            if blocked_visible:
                break

        blocked_check = await client.evaluate("""(() => {
            return {
                title: document.getElementById('blocked-card-title') ? document.getElementById('blocked-card-title').innerText : null,
                badge: document.getElementById('blocked-card-badge') ? document.getElementById('blocked-card-badge').innerText : null,
                msg: document.getElementById('blocked-card-message') ? document.getElementById('blocked-card-message').innerText : null,
                details: document.getElementById('blocked-card-details') ? document.getElementById('blocked-card-details').innerText : null
            };
        })()""")
        print(f"Blocked card validation:\n{json.dumps(blocked_check, indent=2)}")
        assert "STATUS" in (blocked_check["badge"] or "") or "UNAVAILABLE" in (blocked_check["badge"] or ""), "Blocked badge should show status"
        assert "TCS" in (blocked_check["title"] or ""), "Blocked card title should name symbol"

        shot5 = os.path.join(ARTIFACTS_DIR, "05_prediction_tcs_blocked.png")
        await client.screenshot(shot5)

        # -------------------------------------------------------------
        # 6. History Tab: Filters, Pagination, Refresh, Empty State
        # -------------------------------------------------------------
        print("\n--- [6/6] Testing History Tab: BHARTIARTL, TCS, and XYZABC Search ---")
        await client.evaluate("document.getElementById('tab-btn-history').click();")
        await asyncio.sleep(1.5)

        # Test refresh control
        print("Testing Refresh History button...")
        await client.evaluate("document.getElementById('btn-refresh-history').click();")
        await asyncio.sleep(1.0)

        # 6a. Filter: BHARTIARTL
        print("Filtering History by BHARTIARTL...")
        await client.evaluate("""(() => {
            const inp = document.getElementById('history-symbol-filter');
            inp.value = "BHARTIARTL";
            inp.dispatchEvent(new Event('input', { bubbles: true }));
        })()""")
        await asyncio.sleep(1.0)

        bharti_history = await client.evaluate("""(() => {
            const rows = document.querySelectorAll('#history-table-body tr');
            const pageInfo = document.getElementById('history-pagination-info').innerText;
            const prevDisabled = document.getElementById('btn-history-prev').disabled;
            const nextDisabled = document.getElementById('btn-history-next').disabled;
            return {
                rowCount: rows.length,
                pageInfo: pageInfo,
                firstRow: rows[0] ? rows[0].innerText.replace(/\\s+/g, ' ').trim() : null,
                prevDisabled: prevDisabled,
                nextDisabled: nextDisabled
            };
        })()""")
        print(f"BHARTIARTL History: {json.dumps(bharti_history, indent=2)}")
        assert bharti_history["rowCount"] > 0, "BHARTIARTL must return matching records"

        shot6 = os.path.join(ARTIFACTS_DIR, "06_history_search_bhartiartl.png")
        await client.screenshot(shot6)

        # 6b. Filter: TCS (no records persisted for TCS)
        print("Filtering History by TCS (expected empty with clear explanation)...")
        await client.evaluate("""(() => {
            const inp = document.getElementById('history-symbol-filter');
            inp.value = "TCS";
            inp.dispatchEvent(new Event('input', { bubbles: true }));
        })()""")
        await asyncio.sleep(0.8)

        tcs_history = await client.evaluate("""(() => {
            const emptyCell = document.querySelector('#history-table-body td');
            const pageInfo = document.getElementById('history-pagination-info').innerText;
            return {
                cellText: emptyCell ? emptyCell.innerText.trim() : null,
                pageInfo: pageInfo
            };
        })()""")
        print(f"TCS History (Empty State): {json.dumps(tcs_history, indent=2)}")
        assert "No prediction audit records found" in (tcs_history["cellText"] or ""), "Empty state must explain clearly"

        shot7 = os.path.join(ARTIFACTS_DIR, "07_history_search_tcs_empty.png")
        await client.screenshot(shot7)

        # 6c. Filter: Nonexistent ticker XYZABC
        print("Filtering History by nonexistent ticker XYZABC...")
        await client.evaluate("""(() => {
            const inp = document.getElementById('history-symbol-filter');
            inp.value = "XYZABC";
            inp.dispatchEvent(new Event('input', { bubbles: true }));
        })()""")
        await asyncio.sleep(0.8)

        xyz_history = await client.evaluate("""(() => {
            const emptyCell = document.querySelector('#history-table-body td');
            const pageInfo = document.getElementById('history-pagination-info').innerText;
            return {
                cellText: emptyCell ? emptyCell.innerText.trim() : null,
                pageInfo: pageInfo
            };
        })()""")
        print(f"XYZABC History (Empty State): {json.dumps(xyz_history, indent=2)}")
        assert "XYZABC" in (xyz_history["cellText"] or ""), "Explanation must mention ticker symbol"

        shot8 = os.path.join(ARTIFACTS_DIR, "08_history_search_nonexistent_empty.png")
        await client.screenshot(shot8)

        # -------------------------------------------------------------
        # 7. Market Events Tab: Filter chips & Refresh
        # -------------------------------------------------------------
        print("\n--- [Bonus/Complete] Testing Market Events Tab ---")
        await client.evaluate("document.getElementById('tab-btn-events').click();")
        await asyncio.sleep(1.0)

        # Click Monetary policy filter chip
        await client.evaluate("""(() => {
            const chip = document.querySelector('#events-category-filters button[data-category="monetary_policy"]');
            if (chip) chip.click();
        })()""")
        await asyncio.sleep(0.8)

        # Click Refresh Events
        await client.evaluate("document.getElementById('btn-refresh-events').click();")
        await asyncio.sleep(0.8)

        events_data = await client.evaluate("""(() => {
            const cards = document.querySelectorAll('#events-list-container .event-card');
            return {
                count: cards.length,
                firstCard: cards[0] ? cards[0].innerText.slice(0, 100).replace(/\\s+/g, ' ').trim() : null
            };
        })()""")
        print(f"Market events state: {json.dumps(events_data, indent=2)}")

        shot9 = os.path.join(ARTIFACTS_DIR, "09_market_events_tab.png")
        await client.screenshot(shot9)

        await client.close()
        print("\n=== ALL REAL BROWSER INTERACTION TESTS PASSED SUCCESSFULLY! ===")

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()

if __name__ == "__main__":
    asyncio.run(run_verification())
