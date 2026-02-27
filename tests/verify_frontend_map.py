from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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

            # 2. Check Map Mode Toggle
            print("Toggling Map Mode...")
            page.click("#mode-switcher")

            # Check if map container is visible
            map_container = page.locator("#map-container")
            assert map_container.is_visible()
            print("Map container is visible.")

            # 3. Check Chat Bubble Interaction
            print("Interacting with Chat Bubble...")

            # It starts as a bubble? Check if bubble is visible
            # In index.html, bubble has display:flex (via CSS) if chat window is hidden.
            # But wait, our JS toggle logic might have set initial state.
            # Let's check.
            bubble = page.locator("#chat-bubble")
            window = page.locator("#chat-window")

            # Initially bubble should be visible (if we assume default CSS)
            if bubble.is_visible():
                print("Bubble is visible. Clicking to open chat.")
                bubble.click()
                time.sleep(0.5)
                assert window.is_visible()
                print("Chat window opened.")
            else:
                # If window is open by default
                print("Chat window is already open.")
                assert window.is_visible()

            # 4. Send Message with Map Context
            # We are in Map Mode, so bbox should be sent.
            print("Sending message with map context...")
            page.fill("#message-input", "Show me points in this area")
            page.click("button:text('Send')")

            # Wait for user message
            page.wait_for_selector(".message.user")

            # We can't easily verify the backend received the bbox via Playwright without intercepting network or logs.
            # But we can check if no error occurred.
            time.sleep(1)

            # Screenshot
            page.screenshot(path="frontend_map_verification.png")
            print("Screenshot saved to frontend_map_verification.png")

        except Exception as e:
            print(f"Verification Failed: {e}")
            page.screenshot(path="frontend_error.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    verify_frontend()
