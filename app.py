import streamlit as st
import requests
from bs4 import BeautifulSoup
import numpy as np
import openai

# ----------------------------
# STREAMLIT CONFIG
# ----------------------------
st.set_page_config(page_title="Market Price Checker", layout="centered")
st.title("💰 Market Price Intelligence Dashboard")
st.caption("Compare your product prices against the market median using live web scraping and GPT insights.")

# ----------------------------
# OPENAI SETUP (KEY FROM SECRETS)
# ----------------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ----------------------------
# SCRAPER: YOUR PRODUCT PAGE
# ----------------------------
def scrape_product_page(url):
    """Scrape your product page for name and price (RRP)."""
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        # Try to extract name and price
        name = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else "Unknown Product"
        price_el = soup.select_one(".price, .product-price, [data-price]")
        price_text = price_el.get_text(strip=True) if price_el else "0"
        rrp = float(price_text.replace("zł", "").replace(",", ".").replace(" ", ""))

        return {"name": name, "rrp": rrp}
    except Exception as e:
        st.error(f"❌ Error scraping product page: {e}")
        return None

# ----------------------------
# SCRAPER: CENEO (MARKETPLACE)
# ----------------------------
def scrape_ceneo(product_name):
    """Search for the product on Ceneo.pl and extract prices."""
    try:
        search_url = f"https://www.ceneo.pl/;szukaj-{product_name.replace(' ', '+')}"
        html = requests.get(search_url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        price_elements = soup.select(".price")
        prices = []
        for el in price_elements:
            text = el.get_text(strip=True).replace("zł", "").replace(",", ".").replace(" ", "")
            try:
                prices.append(float(text))
            except:
                continue

        return prices
    except Exception as e:
        st.error(f"❌ Error scraping Ceneo: {e}")
        return []

# ----------------------------
# GPT SUMMARY FUNCTION
# ----------------------------
def gpt_summary(name, median, rrp, deviation):
    """Generate a GPT summary comparing RRP to market median."""
    prompt = f"""
Product: {name}
RRP: {rrp:.2f} zł
Median Market Price: {median:.2f} zł
Deviation: {deviation:.1f}%

Summarize this finding in a short, professional business paragraph.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-5",  # or "gpt-4-turbo" if not available
            messages=[{"role": "user", "content": prompt}],
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"❌ GPT Error: {e}")
        return None

# ----------------------------
# STREAMLIT UI
# ----------------------------
product_url = st.text_input("🔗 Enter your product page URL:")

if st.button("Check Price"):
    if not product_url:
        st.warning("Please enter a valid product URL.")
    else:
        with st.spinner("Scraping your product page..."):
            product = scrape_product_page(product_url)

        if product:
            st.subheader(product["name"])
            st.write(f"RRP: **{product['rrp']:.2f} zł**")

            with st.spinner("Scraping market data (Ceneo.pl)..."):
                prices = scrape_ceneo(product["name"])

            if prices:
                median = np.median(prices)
                deviation = (median - product["rrp"]) / product["rrp"] * 100

                st.metric("Median Market Price", f"{median:.2f} zł")
                st.metric("Deviation vs RRP", f"{deviation:.1f}%")

                st.bar_chart(prices)

                with st.spinner("Generating GPT summary..."):
                    summary = gpt_summary(product["name"], median, product["rrp"], deviation)
                if summary:
                    st.markdown("### 🧠 GPT Summary")
                    st.write(summary)
            else:
                st.warning("No prices found on Ceneo — try a different product name.")
