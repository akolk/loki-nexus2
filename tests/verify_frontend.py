from playwright.sync_api import sync_playwright
import time

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to the local app (ensure backend is running!)
        page.goto("http://localhost:8000")

        # Check title
        assert page.title() == "Pydantic AI Workspace"
        print("Title verified")

        # Check sidebar user
        user_el = page.locator("#username")
        assert "researcher_01" in user_el.text_content()
        print("User verified")

        # Simulate chat
        page.fill("#message-input", "Hello from Playwright")
        page.click("button:has-text('Send')")

        # Wait for response (mock agent is fast but async)
        # We look for a message with class 'model'
        try:
            page.wait_for_selector(".message.model", timeout=5000)
            print("Chat response received")
        except:
            print("Chat response timed out (backend might not be running or mocking is off)")

        # Schedule job
        page.fill("#job-query", "Playwright Job")
        page.click("button:has-text('Schedule')")

        # Check status
        page.wait_for_selector("#status", state="visible")
        status_text = page.text_content("#status")
        print(f"Job Status: {status_text}")

        # Screenshot
        page.screenshot(path="frontend_verification.png")
        print("Screenshot saved to frontend_verification.png")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
