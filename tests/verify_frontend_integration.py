from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.main import app
import uvicorn
import threading
import time
from playwright.sync_api import sync_playwright

def run_app():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="critical")

def verify_frontend():
    # Start server in thread
    t = threading.Thread(target=run_app, daemon=True)
    t.start()
    time.sleep(3) # Wait for server startup

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        try:
            # 1. Load Page
            print("Navigating to http://127.0.0.1:8000")
            page.goto("http://127.0.0.1:8000")

            # 2. Verify Title
            title = page.title()
            print(f"Page Title: {title}")
            assert title == "Pydantic AI Workspace"

            # 3. Verify User
            user_el = page.locator("#username")
            assert "researcher_01" in user_el.text_content()
            print("User verified")

            # 4. Simulate Chat (This will fail without API key if not mocked, but UI should update)
            page.fill("#message-input", "Hello Playwright")
            page.click("button:text('Send')")

            # Check if user message appears
            page.wait_for_selector(".message.user")
            print("User message appeared")

            # Wait a bit for potential error or response
            time.sleep(2)

            # 5. Schedule Job
            page.fill("#job-query", "Test Job")
            page.click("button:text('Schedule')")

            # Wait for status update
            time.sleep(1)
            status_text = page.text_content("#status")
            print(f"Status: {status_text}")

            # Screenshot
            page.screenshot(path="frontend_verification.png")
            print("Screenshot saved.")

        except Exception as e:
            print(f"Verification Failed: {e}")
            page.screenshot(path="frontend_error.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    verify_frontend()
