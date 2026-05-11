import threading
import time
import os
import uvicorn
from backend.main import app


def run_server():
    # Run uvicorn in error log level so it doesn't clutter the test output too much
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")


def verify_apeldoorn_map():
    print("Starting Uvicorn Server...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for the server to be ready
    time.sleep(3)

    # Playwright verification
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Set a high timeout for the whole page because the LLM can take a while
            page.set_default_timeout(60000)

            print("Navigating to http://localhost:8000")
            page.goto("http://localhost:8000")

            # --- SCENARIO 1: Map Mode OFF ---
            print("\n--- Starting Scenario 1: Map Mode OFF ---")
            # Open chat bubble if not open
            bubble = page.locator("#chat-bubble")
            window = page.locator("#chat-window")
            if bubble.is_visible():
                print("Opening chat window...")
                bubble.click()
                page.wait_for_selector("#chat-window", state="visible")

            # Make sure map mode is OFF (map container should NOT be visible initially)
            # Actually, map mode defaults to off on page load, let's verify map-container is hidden
            map_container = page.locator("#map-container")
            if map_container.is_visible():
                print("Map mode is ON by default. Turning it OFF...")
                page.evaluate("openSettings()")
                time.sleep(0.5)
                page.click("#mode-switcher")
                page.evaluate("closeSettings()")
                time.sleep(1)
            else:
                print("Map mode is currently OFF.")

            print("Sending query for Apeldoorn center...")
            prompt = (
                "Je moet een kaart laten zien. Genereer Python code die een point geometry maakt voor het "
                "midden van Apeldoorn (lon 5.969, lat 52.21) als een GeoPandas GeoDataFrame en wijs dit toe "
                "aan 'result'. Gebruik GEEN externe bibliotheken zoals matplotlib of folium. Geef geen excuses dat je geen kaarten kan tonen."
            )
            page.fill("#message-input", prompt)
            page.click("button:has-text('Send')")

            # Wait for a post-it note to appear containing a map
            print("Waiting for response (this might take up to 60s for the LLM)...")
            page.wait_for_selector(".postit-note .leaflet-container")
            print("Post-it note with Leaflet map found!")

            # Skip taking screenshot to avoid artifact clutter in repository
            print(
                "Successfully verified Map Mode OFF (No screenshot taken to avoid artifacts)."
            )

            # --- SCENARIO 2: Map Mode ON ---
            print("\n--- Starting Scenario 2: Map Mode ON ---")

            # Refresh the page to clear the previous chat and post-its
            print("Reloading page...")
            page.reload()

            # Reopen chat bubble if closed after reload
            if bubble.is_visible():
                bubble.click()
                page.wait_for_selector("#chat-window", state="visible")

            # Turn Map Mode ON
            print("Toggling Map Mode ON...")
            page.evaluate("openSettings()")
            time.sleep(0.5)
            page.click("#mode-switcher")
            page.evaluate("closeSettings()")

            # Verify map container is visible
            page.wait_for_selector("#map-container", state="visible")
            print("Map container is now visible.")

            print("Sending query for Apeldoorn center...")
            page.fill("#message-input", prompt)
            page.click("button:has-text('Send')")

            # Wait for a map marker or feature to be added to the main map
            print(
                "Waiting for response and map update (this might take up to 60s for the LLM)..."
            )
            # A marker usually creates an img element with class leaflet-marker-icon,
            # or a GeoJSON point might be rendered as an SVG path or a marker.
            # We will wait for a .leaflet-marker-icon inside the #map-container
            page.wait_for_selector("#map-container .leaflet-marker-icon")
            print("Map marker found on the main map!")

            # Skip taking screenshot to avoid artifact clutter in repository
            print(
                "Successfully verified Map Mode ON (No screenshot taken to avoid artifacts)."
            )

            browser.close()

    except Exception as e:
        print(f"Verification failed: {e}")
        # Skip error screenshot to avoid artifact clutter
        pass
        raise e

    print("\nFrontend Apeldoorn map verification passed successfully.")


if __name__ == "__main__":
    verify_apeldoorn_map()
