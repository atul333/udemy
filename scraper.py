import asyncio
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)

# Resource types to block to save CPU and RAM (Crucial for 1GB RAM Ubuntu servers)
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

async def block_unnecessary_resources(route):
    """Abort unnecessary resource requests to save memory and bandwidth."""
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()

def generate_course_url(title: str) -> str:
    """Convert title to Discudemy URL-friendly format."""
    url_title = title.lower()
    url_title = ''.join(c if c.isalnum() else '-' for c in url_title)
    while '--' in url_title:
        url_title = url_title.replace('--', '-')
    url_title = url_title.strip('-')
    return f'https://www.discudemy.com/course/{url_title}'

async def extract_udemy_link_from_page(page: Page, course_url: str) -> str | None:
    """
    Navigate through the course page and its '/go/' redirect page
    to extract the actual Udemy link with coupon code.
    """
    try:
        # Step 1: Visit Discudemy Course Page
        await page.goto(course_url, wait_until="domcontentloaded", timeout=25000)
        
        # Look for the 'Go to course' / 'Take Course' button
        # On Discudemy, this links to /go/...
        go_link_elem = await page.query_selector('a[href*="/go/"]')
        go_url = None
        if go_link_elem:
            href = await go_link_elem.get_attribute('href')
            if href:
                if href.startswith('http'):
                    go_url = href
                else:
                    go_url = 'https://www.discudemy.com' + (href if href.startswith('/') else '/' + href)
        
        if not go_url:
            # Try finding direct Udemy link if already on page
            udemy_elem = await page.query_selector('a[href*="udemy.com/course"]')
            if udemy_elem:
                return await udemy_elem.get_attribute('href')
            logger.warning(f"No /go/ link found on: {course_url}")
            return None

        # Step 2: Visit the /go/ Page
        await page.goto(go_url, wait_until="domcontentloaded", timeout=25000)

        # Step 3: Find Udemy Link with Coupon
        # Discudemy puts it inside a coupon button/link or #couponUrl
        udemy_elem = await page.query_selector('a#couponUrl, a[href*="udemy.com/course"], div.course-coupon a')
        if udemy_elem:
            udemy_url = await udemy_elem.get_attribute('href')
            if udemy_url and 'udemy.com/course' in udemy_url:
                return udemy_url

        # Fallback: Parse page HTML with BeautifulSoup
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        udemy_links = soup.find_all('a', href=lambda x: x and 'udemy.com/course' in x)
        if udemy_links:
            return udemy_links[0]['href']

    except Exception as e:
        logger.error(f"Error resolving Udemy URL for {course_url}: {e}")
    return None

async def get_courses(limit: int = 4, max_pages: int = 3) -> list[dict]:
    """
    Scrape latest Udemy free coupon courses using Playwright with Firefox engine.
    Optimized for Ubuntu Linux servers (low memory footprint).
    """
    courses = []
    seen_urls = set()
    base_url = 'https://www.discudemy.com/all'

    logger.info("Starting Playwright (Firefox) scraper...")

    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        try:
            # Launch Firefox headless with server-friendly flags
            browser = await p.firefox.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )

            # Create an isolated browser context with custom user-agent
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
                viewport={'width': 1280, 'height': 800}
            )

            # Route interception to block images/media (saves RAM & speeds up scraping)
            await context.route("**/*", block_unnecessary_resources)

            page = await context.new_page()

            for page_num in range(1, max_pages + 1):
                list_url = f"{base_url}/{page_num}" if page_num > 1 else base_url
                logger.info(f"Fetching course list from {list_url}")

                try:
                    await page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    logger.error(f"Failed to load {list_url}: {e}")
                    continue

                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Find all course card elements on the list page
                cards = soup.find_all(['section', 'div', 'article'], class_=lambda x: x and any(c in str(x).lower() for c in ['card', 'course', 'content']))
                if not cards:
                    cards = soup.find_all('a', class_=['card-header', 'course-title'])
                
                course_items_to_fetch = []

                for card in cards:
                    try:
                        title_elem = (
                            card.find('a', class_=['card-header', 'course-title']) or
                            card.find(['h3', 'h2', 'h1']) or
                            (card if card.name == 'a' and card.get('href') else None)
                        )
                        if not title_elem:
                            continue

                        title = title_elem.text.strip()
                        if not title or len(title) < 3:
                            continue

                        # Extract course URL on Discudemy
                        href = title_elem.get('href') if title_elem.name == 'a' else None
                        if not href:
                            link_elem = card.find('a', href=True)
                            href = link_elem['href'] if link_elem else None

                        if href:
                            if href.startswith('http'):
                                course_url = href
                            else:
                                course_url = 'https://www.discudemy.com' + (href if href.startswith('/') else '/' + href)
                        else:
                            course_url = generate_course_url(title)

                        if course_url in seen_urls:
                            continue
                        seen_urls.add(course_url)

                        # Extract category
                        cat_elem = card.find(['div', 'a', 'span'], class_=['category', 'course-category', 'cat-links', 'label'])
                        category = 'General'
                        if cat_elem and not any(t in cat_elem.text.lower() for t in ['today', 'yesterday', 'ago', 'min', 'hour']):
                            category = cat_elem.text.strip().replace('Category:', '').strip()

                        # Extract language
                        lang_elem = card.find(['div', 'span'], class_=['language', 'lang'])
                        language = lang_elem.text.strip() if lang_elem else 'English'

                        # Extract date
                        date_elem = card.find(['small', 'span', 'time', 'div'], class_=['date', 'posted-date', 'meta', 'time'])
                        date = date_elem.text.strip() if date_elem else datetime.now().strftime('%Y-%m-%d')


                        course_items_to_fetch.append({
                            'title': title,
                            'url': course_url,
                            'category': category,
                            'language': language,
                            'date': date
                        })

                        if len(courses) + len(course_items_to_fetch) >= limit:
                            break

                    except Exception as item_err:
                        logger.debug(f"Error parsing card: {item_err}")
                        continue

                # Now resolve Udemy coupon links for the found courses
                for item in course_items_to_fetch:
                    logger.info(f"Resolving coupon for: {item['title']}")
                    udemy_url = await extract_udemy_link_from_page(page, item['url'])
                    if udemy_url:
                        item['udemy_url'] = udemy_url
                        courses.append(item)
                        logger.info(f"Found Udemy Coupon URL: {udemy_url}")
                    else:
                        logger.warning(f"Could not get Udemy coupon URL for {item['title']}")

                    if len(courses) >= limit:
                        break

                if len(courses) >= limit:
                    break

        except Exception as e:
            logger.error(f"Error during scraping session: {e}", exc_info=True)
        finally:
            # Ensure resources and browser are strictly closed to prevent zombie processes
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            logger.info("Playwright browser closed cleanly.")

    return courses

# Standalone test runner for debugging directly on server
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("Testing Discudemy scraper with Playwright Firefox...")
    results = asyncio.run(get_courses(limit=2))
    print(f"\nFetched {len(results)} courses:")
    for idx, c in enumerate(results, 1):
        print(f"\n[{idx}] {c['title']}")
        print(f"    Category: {c['category']} | Lang: {c['language']}")
        print(f"    Udemy Link: {c.get('udemy_url')}")