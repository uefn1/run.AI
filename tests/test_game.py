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
        
        # Initial state
        assert "あなたの番です (黒)" in page.inner_text("#turn-indicator")
        assert page.inner_text("#black-score") == "2"
        assert page.inner_text("#white-score") == "2"
        
        # Move 1: Black clicks a hint
        hint_cell = page.locator(".cell.hint").first
        assert hint_cell.count() > 0
        hint_cell.click()
        
        # AI should be thinking
        page.wait_for_timeout(500)
        assert "AI" in page.inner_text("#turn-indicator")
        
        # Wait for AI to complete move
        page.wait_for_timeout(1200)
        assert "あなたの番です (黒)" in page.inner_text("#turn-indicator")
        
        # Verify pieces increased
        black_score = int(page.inner_text("#black-score"))
        white_score = int(page.inner_text("#white-score"))
        assert black_score + white_score > 4
        
        # Test Reset
        page.click("#reset-btn")
        assert page.inner_text("#black-score") == "2"
        assert page.inner_text("#white-score") == "2"
        
        if errors:
            print("Console errors found:", errors)
            raise Exception("Console errors detected")
        
        browser.close()

if __name__ == "__main__":
    test_othello()