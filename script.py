import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import concurrent.futures
from tqdm import tqdm

def check_page(session, page_number, query, agency, top_rated_plus):
    url = f"https://www.upwork.com/nx/search/talent/?nbs=1&q={query}&page={page_number}"
    if agency:
        url += "&pt=agency"
    if top_rated_plus:
        url += "&top_rated_plus=yes"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = session.get(url, headers=headers)
    
    if response.status_code != 200:
        st.error(f"Error: Status code {response.status_code}")
        return False
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check for "No results found" message
    no_results_message = soup.find('h1', string=lambda text: text and "We couldn't find any talent matching your search" in text)
    if no_results_message:
        return False
    
    # Check for freelancer cards
    freelancer_cards = soup.find_all('div', attrs={'data-test': 'freelancer-card'})
    
    if freelancer_cards:
        return True
    
    # Check for any divs that might contain freelancer information
    potential_freelancer_divs = soup.find_all('div', class_=lambda x: x and ('up-card-section' in x or 'freelancer' in x))
    if potential_freelancer_divs:
        return True
    
    return False

def binary_search(session, query, agency, top_rated_plus, max_pages=1000):
    left, right = 1, max_pages
    last_page_with_results = 0
    cache = {}

    total_iterations = (max_pages.bit_length() - 1) * 3  # Estimate of total iterations
    progress_bar = st.progress(0)
    status_text = st.empty()

    iterations = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        while left <= right:
            mid = (left + right) // 2
            pages_to_check = [mid - 1, mid, mid + 1]
            pages_to_check = [p for p in pages_to_check if p > 0 and p not in cache]

            futures = {executor.submit(check_page, session, page, query, agency, top_rated_plus): page for page in pages_to_check}
            for future in concurrent.futures.as_completed(futures):
                page = futures[future]
                result = future.result()
                cache[page] = result
                if result:
                    last_page_with_results = max(last_page_with_results, page)
            
            iterations += 1
            progress = min(1.0, iterations / total_iterations)
            progress_bar.progress(progress)
            status_text.text(f"Searching... Current range: {left} - {right}")

            if cache.get(mid, False):
                left = mid + 1
            else:
                right = mid - 1

            time.sleep(0.05)

    progress_bar.progress(1.0)
    status_text.text("Search complete!")
    return last_page_with_results

def main():
    st.set_page_config(page_title="Upwork Search Page Finder", page_icon="🔍", layout="wide")
    st.title("🔍 Upwork Search Page Finder")

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
            
            with st.spinner(f"Searching for: {query}"):
                start_time = time.time()
                last_page = binary_search(session, query, agency, top_rated_plus)
                end_time = time.time()

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
            st.warning("Please enter a search query.")

if __name__ == "__main__":
    main()
