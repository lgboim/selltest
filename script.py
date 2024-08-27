import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import concurrent.futures
import random

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
    ]
    return random.choice(user_agents)

def check_page(session, page_number, query, agency, top_rated_plus):
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
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return False, f"Error: {str(e)}"
    
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

def binary_search(session, query, agency, top_rated_plus, max_pages=1000):
    left, right = 1, max_pages
    last_page_with_results = 0
    cache = {}

    total_iterations = (max_pages.bit_length() - 1) * 3  # Estimate of total iterations
    iterations = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        while left <= right:
            mid = (left + right) // 2
            pages_to_check = [mid - 1, mid, mid + 1]
            pages_to_check = [p for p in pages_to_check if p > 0 and p not in cache]

            futures = {executor.submit(check_page, session, page, query, agency, top_rated_plus): page for page in pages_to_check}
            for future in concurrent.futures.as_completed(futures):
                page = futures[future]
                result, error = future.result()
                cache[page] = result
                if result:
                    last_page_with_results = max(last_page_with_results, page)
                if error:
                    yield iterations, total_iterations, left, right, None, error
            
            iterations += 1
            yield iterations, total_iterations, left, right, None, None

            if cache.get(mid, False):
                left = mid + 1
            else:
                right = mid - 1

            time.sleep(0.05)

    yield iterations, total_iterations, left, right, last_page_with_results, None

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
            session = requests.Session()
            query = requests.utils.quote(query)
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            start_time = time.time()
            search_generator = binary_search(session, query, agency, top_rated_plus)

            last_page = None
            for result in search_generator:
                iterations, total_iterations, left, right, last_page, error = result
                if error:
                    st.error(error)
                    st.error("The search was blocked. Please try again later or consider using a VPN.")
                    break
                if last_page is not None:
                    break
                progress = min(1.0, iterations / total_iterations)
                progress_bar.progress(progress)
                status_text.text(f"Searching... Current range: {left} - {right}")

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
                st.error("Search failed to complete. Please try again later or consider using a VPN.")

        else:
            st.warning("Please enter a search query.")

if __name__ == "__main__":
    main()
