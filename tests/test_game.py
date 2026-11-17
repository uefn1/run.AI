from playwright.sync_api import sync_playwright
from pathlib import Path

def test_othello():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(exc.text))
        
        html_path = (Path(__file__).resolve().parents[1] / "files" / "index.html").as_uri()
        page.goto(html_path)
        
        # Initial State
        assert "あなたの番です (黒)" in page.inner_text("#turn-indicator")
        assert page.inner_text("#black-score") == "2"
        assert page.inner_text("#white-score") == "2"
        
        # User Move
        hint_cells = page.locator(".cell.hint")
        assert hint_cells.count() > 0
        hint_cells.first.click()
        
        # Wait for transition to AI
        page.wait_for_selector("text=AIが思考中...", timeout=5000)
        
        # Wait for AI turn to end and player turn to return
        page.wait_for_selector("text=あなたの番です (黒)", timeout=10000)
        
        # Score Change
        black_score = int(page.inner_text("#black-score"))
        white_score = int(page.inner_text("#white-score")
        )
        assert black_score + white_score > 4
        
        # Reset Action
        page.click("#reset-btn")
        assert page.inner_text("#black-score") == "2"
        assert page.inner_text("#white-score") == "2"
        assert "あなたの番です (黒)" in page.inner_text("#turn-indicator")
        
        if errors:
            print("Console errors found:", errors)
            raise Exception("Console errors detected")
        
        browser.close()