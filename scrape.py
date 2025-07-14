import json
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

unwanted_keywords = [
    "Costume Events",
    "Events With Choices",
    "Date Events",
    "Secret Events",
    "Events Without Choices"
]

def extract_event_titles(soup):
    heading = soup.find("div", string="Training Events")
    if not heading:
        print("Training Events heading not found.")
        return []

    event_section = heading.find_next_sibling("div")
    if not event_section:
        print("No event section found.")
        return []

    event_titles = []
    for div in event_section.find_all("div"):
        text = div.get_text(strip=True)
        if not text:
            continue
        if any(keyword.lower() in text.lower() for keyword in unwanted_keywords):
            continue
        event_titles.append(text)
    return event_titles

def click_event_card_by_title(page, title):
    page.wait_for_selector("div[class^='compatibility_viewer_item__']")
    candidates = page.locator("div[class^='compatibility_viewer_item__']")
    count = candidates.count()
    # print(f"Found {count} candidate event divs")
    for i in range(count):
        text = candidates.nth(i).text_content().strip()
        if text == title:
            candidates.nth(i).scroll_into_view_if_needed()
            candidates.nth(i).click()
            return True
    return False

def scrape_event_tooltips(page, url):
    event_data = {}

    page.goto(url)
    page.wait_for_selector("text=Training Events")

    # Get rendered HTML and parse event titles with BeautifulSoup
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    event_titles = extract_event_titles(soup)
    print(f"Extracted {len(event_titles)} event titles from {url}")

    for title in event_titles:
        print(f"  Processing event: {title}")
        if not click_event_card_by_title(page, title):
            print(f"  Skipping event '{title}', clickable div not found.")
            continue

        time.sleep(0.4)  # wait for tooltip to appear

        tooltip = page.locator("div[class*='tooltip_container'], div[role='tooltip']")
        if tooltip.count() == 0:
            print(f"  No tooltip found for '{title}', skipping.")
            continue

        td_elements = tooltip.locator("td")
        count = td_elements.count()
        if count <= 1:
            print(f"  Tooltip for '{title}' has 1 or fewer <td> cells, skipping.")
            continue

        options = []
        for i in range(count):
            td = td_elements.nth(i)
            divs = td.locator("div")
            parts = []
            for j in range(divs.count()):
                text = divs.nth(j).text_content().strip()
                if text:
                    parts.append(text)
            option_text = " / ".join(parts).strip()
            if option_text:
                options.append(option_text)

        event_data[title] = options
        print(f"  Added data for '{title}' with {len(options)} options.")

    return event_data

def load_urls(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def get_character_name_from_url(url):
    path = urlparse(url).path
    return path.strip("/").split("/")[-1]

def main():
    data = {
        "supports": {},
        "umas": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Process supports.txt
        supports_urls = load_urls("supports.txt")
        print(f"Processing {len(supports_urls)} URLs from supports.txt")
        for url in supports_urls:
            character = get_character_name_from_url(url)
            print(f"Scraping support character: {character}")
            try:
                event_data = scrape_event_tooltips(page, url)
                data["supports"][character] = event_data
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        # Process umas.txt
        umas_urls = load_urls("umas.txt")
        print(f"Processing {len(umas_urls)} URLs from umas.txt")
        for url in umas_urls:
            character = get_character_name_from_url(url)
            print(f"Scraping uma character: {character}")
            try:
                event_data = scrape_event_tooltips(page, url)
                data["umas"][character] = event_data
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        browser.close()

    # Save to JSON
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Saved results to results.json")

if __name__ == "__main__":
    main()
