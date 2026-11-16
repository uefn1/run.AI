from playwright.sync_api import sync_playwright
from pathlib import Path

def test_othello():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Console error detection
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(exc.text))
        
        html_path = (Path(__file__).resolve().parents[0] / "files" / "index.html").as_uri()
        page.goto(html_path)
        
        # Initial state check
        assert page.inner_text("#turn-indicator") == "あなたの番です (黒)"
        assert page.inner_text("#black-score") == "2"
        assert page.inner_text("#white-score") == "2"
        
        # Find a hint cell and click it
        hint_cell = page.locator(".cell.hint").first
        assert hint_cell.count() > 0
        hint_cell.click()
        
        # Check turn change (AI should start thinking)
        # The turn indicator might change to "AIが思考中..." or "AIの番です (白)"
        page.wait_for_timeout(1000)
        
        # After AI move, it should be black's turn again
        assert "あなたの番です (黒)" in page.inner_text("#turn-indicator")
        
        # Verify scores changed
        black_score = int(page.inner_text("#black-score"))
        white_score = int(page.inner_text("#white-score"))
        assert black_score + white_score > 4
        
        # Reset test
        page.click("#reset-btn")
        assert page.inner_text("#black-score") == "2"
        
        # Final check for errors
        if errors:
            print("Errors found:", errors)
            raise Exception("Console errors detected")
        
        browser.close()

if __name__ == "__main__":
    test_othello()