import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

def generate_course_url(title):
    # Convert title to URL-friendly format
    url_title = title.lower()
    # Replace special characters and spaces with hyphens
    url_title = ''.join(c if c.isalnum() else '-' for c in url_title)
    # Remove consecutive hyphens
    while '--' in url_title:
        url_title = url_title.replace('--', '-')
    # Remove leading/trailing hyphens
    url_title = url_title.strip('-')
    # First get the course page URL
    return f'https://www.discudemy.com/course/{url_title}'

async def get_udemy_urls(session, discudemy_url, headers):
    try:
        # First, get the 'go' page
        async with session.get(discudemy_url, headers=headers, timeout=10) as response:
            if response.status != 200:
                return None
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for the coupon section first
            coupon_section = soup.find('div', class_='course-coupon')
            if coupon_section:
                # Find all Udemy links in the coupon section
                udemy_links = coupon_section.find_all('a', href=lambda x: x and 'udemy.com/course' in x)
            else:
                # If no coupon section, look in the entire page
                udemy_links = soup.find_all('a', href=lambda x: x and 'udemy.com/course' in x)
            
            # Return all valid Udemy URLs found
            valid_urls = []
            seen_urls = set()  # To avoid duplicate URLs
            
            for link in udemy_links:
                url = link['href']
                # Preserve underscore in coupon code
                if 'couponCode=' in url:
                    base_url, params = url.split('?', 1)
                    url = f"{base_url}?{params}"
                
                # Only add unique URLs
                if url not in seen_urls:
                    valid_urls.append(url)
                    seen_urls.add(url)
            
            if not valid_urls:
                print(f'No Udemy link found for {discudemy_url}')
                return None
                
            return valid_urls  # Return all valid URLs found
    except Exception as e:
        print(f'Error fetching Udemy URLs: {str(e)}')
        return None

import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

async def fetch_udemy_urls(session, course_url, headers):
    try:
        # Step 1: Get the course page
        async with session.get(course_url, headers=headers, timeout=10) as response:
            if response.status != 200:
                print(f'Failed to access course page: {course_url}')
                return None
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the 'Go to course' link
            go_link = soup.find('a', class_=['btn', 'button'], href=lambda x: x and '/go/' in x)
            if not go_link:
                print(f'No go link found on course page: {course_url}')
                return None
            
            # Step 2: Get the go page
            href = go_link['href']
            if href.startswith('http'):
                go_url = href
            else:
                go_url = 'https://www.discudemy.com' + (href if href.startswith('/') else '/' + href)
            async with session.get(go_url, headers=headers, timeout=10) as go_response:
                if go_response.status != 200:
                    print(f'Failed to access go page: {go_url}')
                    return None
                go_html = await go_response.text()
                go_soup = BeautifulSoup(go_html, 'html.parser')
                
                # Look for the coupon section first
                coupon_section = go_soup.find('div', class_='course-coupon')
                if coupon_section:
                    udemy_links = coupon_section.find_all('a', href=lambda x: x and 'udemy.com/course' in x)
                else:
                    # If no coupon section, look in the entire page
                    udemy_links = go_soup.find_all('a', href=lambda x: x and 'udemy.com/course' in x)
                
                valid_urls = []
                seen_urls = set()
                
                for link in udemy_links:
                    url = link['href']
                    if 'couponCode=' in url:
                        base_url, params = url.split('?', 1)
                        url = f"{base_url}?{params}"
                    
                    if url not in seen_urls:
                        valid_urls.append(url)
                        seen_urls.add(url)
                
                if not valid_urls:
                    print(f'No Udemy links found on go page: {go_url}')
                    return None
                
                return valid_urls
    except Exception as e:
        print(f'Error fetching Udemy URLs for {course_url}: {str(e)}')
    return None

async def get_courses():
    base_url = 'https://www.discudemy.com/all'
    urls = [f'{base_url}/{i}' for i in range(1, 6)]  # Check first 5 pages to ensure we find enough courses to find more courses
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    
    try:
        courses = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                async with session.get(url, headers=headers, timeout=10) as response:
                    print(f'Response status for {url}: {response.status}')
                    print(f'Response headers: {response.headers}')
                    
                    if response.status != 200:
                        print(f'Failed to fetch page {url}: Status {response.status}')
                        continue
                    
                    html = await response.text()
                
                # Check for common protection systems
                if 'CF-RAY' in response.headers:
                    print('Cloudflare protection detected')
                if any(protection in html.lower() for protection in ['captcha', 'cloudflare', 'ddos-guard', 'protection']):
                    print('Protection system detected in page content')
                
                # Print the first 200 characters of HTML for debugging
                print('First 200 chars of response:')
                print(html[:200])
                
                soup = BeautifulSoup(html, 'html.parser')
                courses = []
                
                # Print the page content for debugging
                print('Page content received, analyzing structure...')
                
                # Try multiple approaches to find course cards
                cards = []
                
                # Approach 1: Find all course containers
                containers = soup.find_all(['div', 'section'], class_=['content', 'course-list', 'courses-list', 'main-content'])
                for container in containers:
                    # Look for cards within containers
                    container_cards = container.find_all(['div', 'article'], class_=lambda x: x and any(c in str(x).lower() for c in ['card', 'course', 'udemy']))
                    cards.extend(container_cards)
                
                if cards:
                    print(f'Found {len(cards)} cards in course containers')
                
                # Approach 2: Direct search throughout the page
                if not cards:
                    cards = soup.find_all(['div', 'article'], class_=lambda x: x and any(c in str(x).lower() for c in ['card', 'course', 'udemy']))
                    if cards:
                        print(f'Found {len(cards)} cards using class name search')
                
                # Final check
                if not cards:
                    print('No course cards found. Analyzing page structure...')
                    # Print the first few elements to understand the structure
                    print('\nPage title:', soup.title.string if soup.title else 'No title found')
                    print('\nFirst level elements:')
                    for elem in soup.find_all(recursive=False)[:5]:  # First 5 top-level elements
                        print(f'- {elem.name}: classes={elem.get("class", [])}')
                    
                    # Look for main content area
                    main_content = soup.find(['main', 'div'], class_=['content', 'main-content', 'courses'])
                    if main_content:
                        print('\nMain content found:')
                        print(f'- Classes: {main_content.get("class", [])}')
                        print('- First level children:')
                        for child in main_content.find_all(recursive=False)[:5]:  # First 5 children
                            print(f'  * {child.name}: classes={child.get("class", [])}')
                    else:
                        print('\nNo main content area found with expected classes')
                        
                    # Try to find any div with 'course' or 'card' in its class
                    course_related = soup.find_all('div', class_=lambda x: x and ('course' in x.lower() or 'card' in x.lower()))
                    if course_related:
                        print(f'\nFound {len(course_related)} elements with course/card in class name:')
                        for elem in course_related[:3]:  # Show first 3
                            print(f'- {elem.name}: classes={elem.get("class", [])}')
                    
                    return []
                
                print(f'Successfully found {len(cards)} course cards on {url}')
                # Add courses from this page
                page_tasks = []
                remaining_slots = 4 - len(courses)
                if remaining_slots <= 0:
                    break
                    
                for card in cards[:remaining_slots]:  # Only process enough cards to reach total of 4
                    try:
                        # Try different possible selectors for title
                        title_elem = (
                            card.find('a', class_=['card-header', 'course-title']) or
                            card.find(['h3', 'h2', 'h1']) or
                            card.find('a', href=True)
                        )
                        
                        # Try different possible selectors for date
                        date_elem = (
                            card.find('small', class_='date') or
                            card.find(['span', 'time'], class_=['date', 'posted-date']) or
                            card.find(['span', 'time'])
                        )
                        
                        # Get language
                        lang_elem = card.find_previous('div', class_=['language', 'lang']) or \
                                   card.find_parent('div', class_=['language', 'lang'])
                        language = lang_elem.text.strip() if lang_elem else 'English'

                        # Try different possible selectors for category
                        category_elem = (
                            card.find('div', class_=['category', 'course-category', 'cat-links']) or
                            card.find('a', class_=['category', 'course-category']) or
                            card.find('span', class_=['category', 'course-category']) or
                            card.find('div', string=lambda s: s and any(cat in s.lower() for cat in ['business', 'development', 'finance', 'it', 'office', 'personal', 'design', 'marketing', 'lifestyle', 'photography', 'health', 'music']))
                        )
                        
                        if title_elem and date_elem:
                            title = title_elem.text.strip()
                            date = date_elem.text.strip()
                            category = category_elem.text.strip().lower() if category_elem else 'other'
                            
                            if title and date:  # Only add if both fields are non-empty
                                course_url = generate_course_url(title)
                                print(f'Processing course: {title} at {course_url}')
                                # Add task to fetch Udemy URLs
                                task = fetch_udemy_urls(session, course_url, headers)
                                page_tasks.append((task, {
                                    'title': title,
                                    'date': date,
                                    'category': category.replace('Category:', '').strip() if category else 'other',
                                    'url': course_url,
                                    'language': language
                                }))
                    except Exception as card_error:
                        print(f'Error processing card: {str(card_error)}')
                        continue
                
                # Process tasks for this page
                if page_tasks:
                    results = await asyncio.gather(*[task[0] for task in page_tasks])
                    
                    # Process results
                    for (_, course_info), udemy_urls in zip(page_tasks, results):
                        if udemy_urls:
                            for udemy_url in udemy_urls:
                                course_data = course_info.copy()
                                course_data['udemy_url'] = udemy_url
                                courses.append(course_data)
                                
                    # Break if we have enough courses
                    if len(courses) >= 4:
                        break
        
        return courses
    except aiohttp.ClientError as e:
        print(f'Network error: {str(e)}')
        return []
    except Exception as e:
        print(f'Error fetching courses: {str(e)}')
        return []