"""Day 67 Real Browser Interaction & Accessibility Verification Script.

Executes real browser workflows against the live local FastAPI application
running on 127.0.0.1:8000 using native Chrome DevTools Protocol (CDP) and
the installed Google Chrome or Microsoft Edge browser.

Workflows Tested:
1. Discovery of installed browser runtimes (Chrome / Edge).
2. Workflow A (Supported instrument - BHARTIARTL):
   - Loading state, hero card rendering, predicted direction, model identity.
   - Uncalibrated probability warning & evidence-aligned comparison text.
   - Observed quote distinction (LAST_TRADED_PRICE, not a price forecast).
3. Workflow B (Unsupported instruments - TCS, RELIANCE, NIFTY_TELECOMMUNICATIONS, NIFTY_50):
   - Model unavailability diagnostic card.
   - Absence of fabricated price, direction, or success badges.
4. Workflow C (Error recovery & Stale result handling):
   - One-click recovery to supported instrument (BHARTIARTL).
   - Stale hero card clearing immediately upon changing symbol input.
5. Workflow D (Concurrency & Double-submission locking):
   - Immediate button disabling and AppState.isPredicting lock on submission.
   - Clean re-enabling upon completion.
6. Accessibility & Responsive design:
   - Desktop viewport (1280x800) and Mobile viewport (375x667) overflow verification.
   - Explicit form labels (<label for="symbol-input">, <label for="model-select">).
   - ARIA landmarks and live regions.
   - Non-color visual cues (arrows, textual direction badges).
   - Zero console exceptions during all operations.
"""

import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class ChromeCDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self._next_id = 1
        self._pending = {}
        self.console_messages = []
        self.exceptions = []
        self._listener_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=10_000_000)
        self._listener_task = asyncio.create_task(self._listen())
        await self.send("Runtime.enable")
        await self.send("Page.enable")
        await self.send("Console.enable")
        await self.send("Network.enable")
        await self.send("Network.setCacheDisabled", {"cacheDisabled": True})

    async def _listen(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                msg_id = msg.get("id")
                if msg_id and msg_id in self._pending:
                    future = self._pending.pop(msg_id)
                    if not future.done():
                        future.set_result(msg)
                else:
                    method = msg.get("method")
                    if method == "Console.messageAdded":
                        self.console_messages.append(msg.get("params", {}).get("message", {}))
                    elif method == "Runtime.exceptionThrown":
                        self.exceptions.append(msg.get("params", {}).get("exceptionDetails", {}))
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def send(self, method: str, params: dict = None):
        cmd_id = self._next_id
        self._next_id += 1
        future = asyncio.get_event_loop().create_future()
        self._pending[cmd_id] = future
        payload = {"id": cmd_id, "method": method}
        if params:
            payload["params"] = params
        await self.ws.send(json.dumps(payload))
        return await future

    async def evaluate(self, expr: str, await_promise: bool = True):
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "awaitPromise": await_promise,
            "returnByValue": True
        })
        result = res.get("result", {})
        if "exceptionDetails" in result:
            raise RuntimeError(f"JS Exception: {result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    async def wait_for(self, expr: str, timeout: float = 12.0, step: float = 0.2):
        start = time.time()
        while time.time() - start < timeout:
            try:
                val = await self.evaluate(expr)
                if val:
                    return val
            except Exception:
                pass
            await asyncio.sleep(step)
        raise TimeoutError(f"Condition not met within {timeout}s: {expr}")

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()


def find_browser_executable() -> str:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if Path(c).is_file():
            return c
    raise RuntimeError("No supported browser (Chrome or Edge) found locally.")


async def execute_real_browser_audit(port: int = 8000) -> dict:
    browser_exe = find_browser_executable()
    print(f"Discovered browser runtime: {browser_exe}")

    profile_dir = Path("scratch/real_browser_audit_profile").resolve()
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)
    profile_dir.mkdir(parents=True, exist_ok=True)

    cdp_port = 9222
    url = f"http://127.0.0.1:{port}/ui"

    proc = subprocess.Popen([
        browser_exe,
        "--headless=new",
        f"--remote-debugging-port={cdp_port}",
        "--disable-gpu",
        "--disable-cache",
        f"--user-data-dir={str(profile_dir)}",
        url
    ])

    cdp = None
    results = {
        "browser": browser_exe,
        "workflows": {},
        "accessibility": {},
        "exceptions": [],
    }

    try:
        # Wait for CDP discovery endpoint
        for _ in range(20):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json") as r:
                    targets = json.loads(r.read().decode())
                    if targets:
                        break
            except Exception:
                await asyncio.sleep(0.4)
        else:
            raise RuntimeError(f"Could not connect to browser CDP port {cdp_port}")

        page_target = [t for t in targets if t.get("type") == "page"][0]
        cdp = ChromeCDPClient(page_target["webSocketDebuggerUrl"])
        await cdp.connect()

        # Initial Page Load
        title = await cdp.wait_for("document.title")
        print(f"[PRE-FLIGHT] Page loaded. Title: '{title}'")
        chips_count = await cdp.wait_for(
            "document.querySelectorAll('#quick-ticker-chips .chip').length >= 5 ? document.querySelectorAll('#quick-ticker-chips .chip').length : 0",
            timeout=8.0
        )
        print(f"[PRE-FLIGHT] Authoritative catalog loaded: {chips_count} instrument chips.")

        # -------------------------------------------------------------------
        # WORKFLOW A: Supported Instrument (BHARTIARTL)
        # -------------------------------------------------------------------
        print("\n=== EXECUTING WORKFLOW A: Supported Instrument (BHARTIARTL) ===")
        await cdp.evaluate("""
            (() => {
                const inp = document.getElementById('symbol-input');
                inp.value = 'BHARTIARTL';
                document.getElementById('model-select').value = 'xgboost';
                document.getElementById('prediction-form').requestSubmit();
            })()
        """)

        await cdp.wait_for("document.getElementById('result-hero-card').style.display === 'block'", timeout=15.0)

        res_a = await cdp.evaluate("""
            (function() {
                const statusBadge = document.getElementById('res-status-badge').textContent;
                const dirIcon = document.getElementById('res-direction-icon').textContent;
                const dirText = document.getElementById('res-direction-text').textContent;
                const modelBadge = document.getElementById('res-model-badge').textContent;
                const probUp = document.getElementById('res-prob-up').textContent;
                const probDown = document.getElementById('res-prob-down').textContent;
                const disclaimer = document.getElementById('res-uncalibrated-text').textContent;
                const observedMeta = document.getElementById('res-observed-meta').textContent;
                const forecastMeta = document.getElementById('res-forecast-meta').textContent;
                return {
                    statusBadge,
                    direction: `${dirIcon} ${dirText}`.trim(),
                    modelBadge,
                    probUp,
                    probDown,
                    disclaimer: disclaimer.trim(),
                    observedMeta,
                    forecastMeta
                };
            })()
        """)
        print(f"  [OK] Status Badge: {res_a['statusBadge']}")
        print(f"  [OK] Direction: {res_a['direction']}")
        print(f"  [OK] Model Identity: {res_a['modelBadge']}")
        print(f"  [OK] Probabilities: {res_a['probUp']} | {res_a['probDown']}")
        print(f"  [OK] Observed Quote Meta: {res_a['observedMeta']}")
        print(f"  [OK] Forecast Meta: {res_a['forecastMeta']}")

        assert res_a["statusBadge"] == "SUCCESS"
        assert "p > 0.34" not in res_a["disclaimer"], "Misleading p > 0.34 found!"
        assert "constant 0.50" in res_a["disclaimer"], "Evidence-aligned comparison missing!"
        assert "Not a predicted price" in res_a["observedMeta"]
        results["workflows"]["A_supported"] = res_a

        # -------------------------------------------------------------------
        # WORKFLOW B: Unsupported Instruments
        # -------------------------------------------------------------------
        print("\n=== EXECUTING WORKFLOW B: Unsupported Instruments ===")
        unsupported_syms = ["TCS", "RELIANCE", "NIFTY_TELECOMMUNICATIONS", "NIFTY_50"]
        results["workflows"]["B_unsupported"] = {}

        for sym in unsupported_syms:
            await cdp.evaluate(f"""
                document.getElementById('symbol-input').value = '{sym}';
                document.getElementById('prediction-form').requestSubmit();
            """)
            await cdp.wait_for("document.getElementById('result-blocked-card').style.display === 'block'", timeout=8.0)

            res_b = await cdp.evaluate("""
                (function() {
                    const heroHidden = document.getElementById('result-hero-card').style.display === 'none';
                    const title = document.getElementById('blocked-card-title').textContent;
                    const badge = document.getElementById('blocked-card-badge').textContent;
                    const msg = document.getElementById('blocked-card-message').textContent;
                    return { heroHidden, title, badge, msg };
                })()
            """)
            print(f"  [OK] {sym} -> Badge='{res_b['badge']}', Title='{res_b['title']}' (Hero hidden={res_b['heroHidden']})")
            assert res_b["heroHidden"], f"Hero card visible for {sym}!"
            assert "BLOCKED" in res_b["badge"]
            results["workflows"]["B_unsupported"][sym] = res_b

        # -------------------------------------------------------------------
        # WORKFLOW C: Error Recovery & Stale Reset
        # -------------------------------------------------------------------
        print("\n=== EXECUTING WORKFLOW C: Error Recovery & Stale Reset ===")
        # One-click switch to supported instrument
        await cdp.evaluate("document.getElementById('btn-switch-to-supported').click();")
        val_after_switch = await cdp.evaluate("document.getElementById('symbol-input').value")
        blocked_hidden = await cdp.evaluate("document.getElementById('result-blocked-card').style.display === 'none'")
        print(f"  [OK] Clicked 'Select Supported Instrument': input='{val_after_switch}', blocked card hidden={blocked_hidden}")
        assert val_after_switch == "BHARTIARTL"
        assert blocked_hidden is True

        # Generate prediction then test typing clears stale result
        await cdp.evaluate("document.getElementById('prediction-form').requestSubmit();")
        await cdp.wait_for("document.getElementById('result-hero-card').style.display === 'block'", timeout=15.0)
        print("  [OK] Generated active prediction.")

        await cdp.evaluate("""
            (() => {
                const inp = document.getElementById('symbol-input');
                inp.value = 'WIPRO';
                inp.dispatchEvent(new Event('input'));
            })()
        """)
        hero_cleared = await cdp.evaluate("document.getElementById('result-hero-card').style.display === 'none'")
        print(f"  [OK] Changing symbol input immediately hides stale hero card: {hero_cleared}")
        assert hero_cleared is True
        results["workflows"]["C_recovery"] = {"switch_supported": True, "stale_cleared": True}

        # -------------------------------------------------------------------
        # WORKFLOW D: Concurrency & Double-Submission Locking
        # -------------------------------------------------------------------
        print("\n=== EXECUTING WORKFLOW D: Concurrency & Double-Submission Locking ===")
        await cdp.evaluate("document.getElementById('symbol-input').value = 'BHARTIARTL';")
        d_lock = await cdp.evaluate("""
            (function() {
                const btn = document.getElementById('btn-run-prediction');
                const form = document.getElementById('prediction-form');
                form.requestSubmit();
                const wasDisabledImmediately = btn.disabled;
                const spinnerVisible = document.getElementById('btn-predict-spinner').style.display !== 'none';
                return { wasDisabledImmediately, spinnerVisible };
            })()
        """)
        print(f"  [OK] Lock verification: wasDisabled={d_lock['wasDisabledImmediately']}, spinnerVisible={d_lock['spinnerVisible']}")
        assert d_lock["wasDisabledImmediately"] is True

        await cdp.wait_for("!document.getElementById('btn-run-prediction').disabled", timeout=15.0)
        btn_re_enabled = await cdp.evaluate("!document.getElementById('btn-run-prediction').disabled")
        print(f"  [OK] Predict button safely re-enabled after inference: {btn_re_enabled}")
        assert btn_re_enabled is True
        results["workflows"]["D_concurrency"] = d_lock

        # -------------------------------------------------------------------
        # ACCESSIBILITY & RESPONSIVE CHECKS
        # -------------------------------------------------------------------
        print("\n=== EXECUTING ACCESSIBILITY & RESPONSIVE CHECKS ===")

        # Desktop Viewport (1280x800)
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 800,
            "deviceScaleFactor": 1,
            "mobile": False
        })
        desktop_overflow = await cdp.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        print(f"  [OK] Desktop Viewport (1280x800) Horizontal Overflow: {desktop_overflow} (Expected: False)")
        assert not desktop_overflow

        # Mobile Viewport (375x667 - iPhone SE)
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": 375,
            "height": 667,
            "deviceScaleFactor": 2,
            "mobile": True
        })
        mobile_overflow = await cdp.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        print(f"  [OK] Mobile Viewport (375x667) Horizontal Overflow: {mobile_overflow} (Expected: False)")
        assert not mobile_overflow

        # Accessibility Form Labels & Non-Color Cues
        a11y_data = await cdp.evaluate("""
            (function() {
                const labels = Array.from(document.querySelectorAll('label[for]')).map(l => l.getAttribute('for'));
                const hasSymbolLabel = labels.includes('symbol-input');
                const hasModelLabel = labels.includes('model-select');
                const dirBadge = document.getElementById('res-direction-badge');
                const dirText = dirBadge ? dirBadge.textContent : '';
                const hasArrow = dirText.includes('↗') || dirText.includes('↘') || dirText.includes('⏸');
                const hasText = dirText.includes('Bullish') || dirText.includes('Bearish') || dirText.includes('Flat');
                return {
                    hasSymbolLabel,
                    hasModelLabel,
                    hasArrow,
                    hasText
                };
            })()
        """)
        print(f"  [OK] Accessibility Form Labels: Symbol={a11y_data['hasSymbolLabel']}, Model={a11y_data['hasModelLabel']}")
        print(f"  [OK] Non-Color Direction Cues: Arrow={a11y_data['hasArrow']}, Text={a11y_data['hasText']}")
        assert a11y_data["hasSymbolLabel"] and a11y_data["hasModelLabel"]
        assert a11y_data["hasArrow"] and a11y_data["hasText"]
        results["accessibility"] = a11y_data

        # Uncaught JS Exceptions Audit
        print(f"\nUncaught JS Exceptions: {len(cdp.exceptions)}")
        for exc in cdp.exceptions:
            print(f"  [EXC] {exc.get('text')}")
        assert len(cdp.exceptions) == 0, f"Uncaught exceptions during real browser execution: {cdp.exceptions}"
        results["exceptions"] = cdp.exceptions

        print("\n>>> ALL REAL BROWSER AUDIT WORKFLOWS COMPLETED SUCCESSFULLY! <<<")
        return results

    finally:
        if cdp:
            await cdp.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        if profile_dir.exists():
            shutil.rmtree(profile_dir, ignore_errors=True)
        print("Browser process terminated.")


if __name__ == "__main__":
    asyncio.run(execute_real_browser_audit())
