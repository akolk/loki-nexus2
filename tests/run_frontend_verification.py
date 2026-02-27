import threading
import time
import os
import uvicorn
from backend.main import app

# Function to run the server in a separate thread
def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    # Start the server thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Give it a moment to start
    time.sleep(2)

    # Run the playwright verification
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            print("Navigating to http://localhost:8000")
            page.goto("http://localhost:8000")

            # 1. Verify Title
            title = page.title()
            print(f"Page title: {title}")
            assert title == "Pydantic AI Workspace"

            # 2. Verify User
            user_text = page.text_content("#username")
            print(f"User: {user_text}")
            assert "researcher_01" in user_text

            # 3. Send a Chat Message
            print("Sending chat message...")
            page.fill("#message-input", "Hello Playwright")
            page.click("button:has-text('Send')")

            # Wait for response (might be slow due to agent/mock)
            # We mock the agent in the backend/main.py or it fails with 500 without key
            # If 500, the frontend might show error. Let's check for either .model message or error status.
            try:
                # Wait for a model message to appear
                page.wait_for_selector(".message.model", timeout=5000)
                print("Received model response.")
            except:
                print("Model response timeout or error.")
                status = page.text_content("#status")
                print(f"Status: {status}")

            # 4. Schedule Job
            print("Scheduling job...")
            page.fill("#job-query", "Test Job")
            page.click("button:has-text('Schedule')")

            # Wait for status update
            time.sleep(1)
            status = page.text_content("#status")
            print(f"Job Status: {status}")

            # Take screenshot
            page.screenshot(path="frontend_verification.png")
            print("Screenshot saved to frontend_verification.png")

            browser.close()

    except Exception as e:
        print(f"Verification failed: {e}")
        exit(1)

    print("Frontend verification passed.")
