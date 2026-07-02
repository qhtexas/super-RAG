from playwright.sync_api import sync_playwright,Page

def get_question(url: str, page: Page):
    page.goto(url)
