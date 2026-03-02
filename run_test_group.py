from playwright.sync_api import sync_playwright

def test_frontend_group():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('file:///app/frontend/index.html')

        page.evaluate("""
            createPostit({type: "html", content: "Note 1"});
            createPostit({type: "html", content: "Note 2"});

            // manually trigger the logic to create a group
            const notes = document.querySelectorAll('.postit-note');
            createGroup([notes[0], notes[1]], 300, 300);
        """)

        page.screenshot(path="frontend_grouped.png")

        browser.close()

test_frontend_group()
