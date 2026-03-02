from playwright.sync_api import sync_playwright

def test_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('file:///app/frontend/index.html')

        # Test chat bubble opens window correctly
        page.locator("#chat-bubble").click()
        page.screenshot(path="frontend_chat_opened.png")

        # Mock an execResult being received to test postit creation
        page.evaluate("""
            appendMessage("model", "Here is your data", {
                type: "dataframe",
                content: "<table class='dataframe'><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
            });
            appendMessage("model", "Another note", {
                type: "html",
                content: "<b>Bold HTML</b>"
            });
        """)

        page.screenshot(path="frontend_postits.png")

        browser.close()

test_frontend()
