import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import time
import random

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
    ]
    return random.choice(user_agents)

def check_page(page_number, query, agency, top_rated_plus):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    url = f"https://www.upwork.com/nx/search/talent/?nbs=1&q={query}&page={page_number}"
    if agency:
        url += "&pt=agency"
    if top_rated_plus:
        url += "&top_rated_plus=yes"
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.upwork.com/',
        'DNT': '1',
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for "No results found" message
            no_results_message = soup.find('h1', string=lambda text: text and "We couldn't find any talent matching your search" in text)
            if no_results_message:
                return False, None

            # Check for freelancer cards
            freelancer_cards = soup.find_all('div', attrs={'data-test': 'freelancer-card'})
            
            if freelancer_cards:
                return True, None
            
            # Check for any divs that might contain freelancer information
            potential_freelancer_divs = soup.find_all('div', class_=lambda x: x and ('up-card-section' in x or 'freelancer' in x))
            if potential_freelancer_divs:
                return True, None
            
            return False, None

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                return False, f"Error: {str(e)}"

def linear_search(query, agency, top_rated_plus, max_pages=1000):
    last_page_with_results = 0
    page = 1

    while page <= max_pages:
        time.sleep(random.uniform(5, 10))  # Random delay between 5 and 10 seconds
        
        result, error = check_page(page, query, agency, top_rated_plus)
        
        if error:
            yield page, max_pages, None, error
            break
        
        if result:
            last_page_with_results = page
            yield page, max_pages, None, None
            page += 1
        else:
            if page > last_page_with_results + 5:  # Stop if no results for 5 consecutive pages
                break
            page += 1

    yield page, max_pages, last_page_with_results, None

def main():
    st.set_page_config(page_title="Upwork Search Page Finder", page_icon="🔍", layout="wide")
    st.title("🔍 Upwork results")

    col1, col2 = st.columns([2, 1])

    with col1:
        query = st.text_input("Enter your search query:")
    with col2:
        agency = st.checkbox("Search for agencies")
        top_rated_plus = st.checkbox("Search for Top Rated Plus")

    if st.button("Search", type="primary"):
        if query:
            query = cloudscraper.utils.quote(query)
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            start_time = time.time()
            search_generator = linear_search(query, agency, top_rated_plus)

            last_page = None
            for result in search_generator:
                current_page, max_pages, last_page, error = result
                if error:
                    st.error(error)
                    st.error("The search was blocked. Please try again later.")
                    break
                if last_page is not None:
                    break
                progress = min(1.0, current_page / max_pages)
                progress_bar.progress(progress)
                status_text.text(f"Searching... Current page: {current_page}")

            end_time = time.time()

            if last_page is not None:
                progress_bar.progress(1.0)
                status_text.text("Search complete!")

                st.success("Search complete!")

                # Results container
                results_container = st.container()
                with results_container:
                    st.subheader("Search Results")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Last Page with Results", last_page)
                        st.metric("Total Results (Approx.)", last_page * 10)
                    
                    with col2:
                        st.metric("Time Taken", f"{end_time - start_time:.2f} seconds")

                    st.subheader("Last Page URL")
                    url = f"https://www.upwork.com/nx/search/talent/?nbs=1&q={query}"
                    if agency:
                        url += "&pt=agency"
                    if top_rated_plus:
                        url += "&top_rated_plus=yes"
                    url += f"&page={last_page}"
                    st.markdown(f"[Open Last Page]({url})")

                    st.subheader("Search Parameters")
                    st.json({
                        "Query": query,
                        "Agency": "Yes" if agency else "No",
                        "Top Rated Plus": "Yes" if top_rated_plus else "No"
                    })
            else:
                st.error("Search failed to complete. Please try again later.")

        else:
            st.warning("Please enter a search query.")

if __name__ == "__main__":
    main()
