import requests
from bs4 import BeautifulSoup
from datetime import datetime

def generate_course_url(category, title):
    # Convert title to URL-friendly format
    url_title = title.lower()
    # Replace special characters and spaces with hyphens
    url_title = ''.join(c if c.isalnum() else '-' for c in url_title)
    # Remove consecutive hyphens
    while '--' in url_title:
        url_title = url_title.replace('--', '-')
    # Remove leading/trailing hyphens
    url_title = url_title.strip('-')
    return f'https://www.discudemy.com/go/{url_title}'

def get_udemy_url(discudemy_url, headers):
    try:
        # First, get the 'go' page
        response = requests.get(discudemy_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the Course Coupon section
        coupon_section = soup.find('div', class_='course-coupon')
        if coupon_section:
            # Find the Udemy URL in the coupon section
            udemy_link = coupon_section.find('a', href=lambda x: x and 'udemy.com/course' in x)
            if udemy_link:
                return udemy_link['href']
        
        # If not found in coupon section, try finding any Udemy link
        udemy_link = soup.find('a', href=lambda x: x and 'udemy.com/course' in x)
        if udemy_link:
            return udemy_link['href']
            
        print(f'No Udemy link found for {discudemy_url}')
        return None
    except Exception as e:
        print(f'Error fetching Udemy URL: {str(e)}')
        return None

def get_courses():
    url = 'https://www.discudemy.com/all'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        soup = BeautifulSoup(response.text, 'html.parser')
        courses = []
        
        # Try different possible class names for course cards
        cards = soup.find_all(['div', 'article'], class_=['card', 'course-card', 'coursed-card'])
        
        if not cards:
            # If no cards found, try finding by article tag
            cards = soup.find_all('article')
        
        for card in cards[:5]:  # Get first 5 courses
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
                
                # Try different possible selectors for category
                category_elem = (
                    card.find('span', class_=['category', 'course-category']) or
                    card.find('a', class_=['category', 'course-category']) or
                    card.find(['span', 'a'], string=lambda s: s and any(cat in s.lower() for cat in ['business', 'development', 'finance', 'it', 'office', 'personal', 'design', 'marketing', 'lifestyle', 'photography', 'health', 'music']))
                )
                
                if title_elem and date_elem:
                    title = title_elem.text.strip()
                    date = date_elem.text.strip()
                    category = category_elem.text.strip().lower() if category_elem else 'other'
                    
                    if title and date:  # Only add if both fields are non-empty
                        course_url = generate_course_url(category, title)
                        udemy_url = get_udemy_url(course_url, headers)
                        courses.append({
                            'title': title,
                            'date': date,
                            'category': category,
                            'url': course_url,
                            'udemy_url': udemy_url
                        })
            except Exception as card_error:
                print(f'Error processing card: {str(card_error)}')
                continue
        
        return courses
    except requests.RequestException as e:
        print(f'Network error: {str(e)}')
        return []
    except Exception as e:
        print(f'Error fetching courses: {str(e)}')
        return []