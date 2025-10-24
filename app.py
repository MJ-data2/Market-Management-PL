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
                import streamlit as st
import requests
from bs4 import BeautifulSoup
import numpy as np
import openai
import time

# ----------------------------
# STREAMLIT CONFIG
# ----------------------------
st.set_page_config(page_title="Market Price Intelligence", layout="centered")
st.title("💰 Multi-Marketplace Price Intelligence Dashboard")
st.caption("Scrapes Ceneo, Allegro, Amazon and Google Shopping — compares prices vs RRP, and summarizes with GPT.")

# ----------------------------
# OPENAI CONFIG (from Streamlit Secrets)
# ----------------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ----------------------------
# SCRAPER HELPERS
# ----------------------------
def safe_float(text):
    """Clean PLN price strings."""
    text = text.replace("zł", "").replace(",", ".").replace(" ", "")
    return float(text)

# --- Your product page ---
def scrape_product_page(url):
    """Scrape your product page for name and RRP."""
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    name = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else "Unknown Product"
    price_el = soup.select_one(".price, .product-price, [data-price]")
    price_text = price_el.get_text(strip=True) if price_el else "0"
    rrp = safe_float(price_text)
    return {"name": name, "rrp": rrp}

# --- Ceneo.pl ---
def scrape_ceneo(product_name):
    url = f"https://www.ceneo.pl/;szukaj-{product_name.replace(' ', '+')}"
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for el in soup.select(".price"):
        try:
            prices.append(safe_float(el.get_text(strip=True)))
        except:
            continue
    return prices

# --- Allegro.pl ---
def scrape_allegro(product_name):
    url = f"https://allegro.pl/listing?string={product_name.replace(' ', '%20')}"
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for el in soup.select("span._9c44d_1zemI span"):
        try:
            prices.append(safe_float(el.get_text(strip=True)))
        except:
            continue
    return prices

# --- Amazon.pl ---
def scrape_amazon(product_name):
    url = f"https://www.amazon.pl/s?k={product_name.replace(' ', '+')}"
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for el in soup.select("span.a-price-whole"):
        try:
            prices.append(safe_float(el.get_text(strip=True)))
        except:
            continue
    return prices

# --- Google Shopping ---
def scrape_google_shopping(product_name):
    url = f"https://www.google.com/search?tbm=shop&q={product_name.replace(' ', '+')}"
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for el in soup.select("span.a8Pemb"):
        try:
            prices.append(safe_float(el.get_text(strip=True)))
        except:
            continue
    return prices

# ----------------------------
# AGGREGATOR
# ----------------------------
def aggregate_prices(product_name):
    """Collect prices from all supported sites."""
    results = {}
    for site, fn in {
        "Ceneo": scrape_ceneo,
        "Allegro": scrape_allegro,
        "Amazon": scrape_amazon,
        "Google": scrape_google_shopping,
    }.items():
        try:
            st.write(f"🔍 Searching **{site}** ...")
            prices = fn(product_name)
            results[site] = prices
            time.sleep(1)  # polite delay
        except Exception as e:
            st.warning(f"{site} error: {e}")
            results[site] = []
    all_prices = [p for site_prices in results.values() for p in site_prices]
    return all_prices, {site: len(p) for site, p in results.items()}

# ----------------------------
# GPT SUMMARY
# ----------------------------
def gpt_summary(name, median, rrp, deviation, site_counts):
    prompt = f"""
Product: {name}
RRP: {rrp:.2f} zł
Median Market Price: {median:.2f} zł
Deviation: {deviation:.1f}%
Listings: {site_counts}

Summarize in 1 paragraph which marketplaces are cheaper or more expensive,
and what this means versus RRP.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-5",  # or gpt-4-turbo
            messages=[{"role": "user", "content": prompt}],
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"GPT Error: {e}")
        return None

# ----------------------------
# STREAMLIT INTERFACE
# ----------------------------
product_url = st.text_input("🔗 Enter your product page URL:", key="product_url_input")
if st.button("Check Market Prices"):
    if not product_url:
        st.warning("Please enter a valid product URL.")
        st.stop()

    with st.spinner("Scraping your product page..."):
        product = scrape_product_page(product_url)

    st.subheader(product["name"])
    st.write(f"RRP: **{product['rrp']:.2f} zł**")

    with st.spinner("Scraping multiple marketplaces..."):
        all_prices, site_counts = aggregate_prices(product["name"])

    if all_prices:
        median = np.median(all_prices)
        deviation = (median - product["rrp"]) / product["rrp"] * 100
        st.metric("Median Market Price", f"{median:.2f} zł")
        st.metric("Deviation vs RRP", f"{deviation:.1f}%")
        st.write("🛍️ Listings found per site:", site_counts)
        st.bar_chart(all_prices)

        with st.spinner("Generating GPT summary..."):
            summary = gpt_summary(product["name"], median, product["rrp"], deviation, site_counts)
        if summary:
            st.markdown("### 🧠 GPT Summary")
            st.write(summary)
    else:
        st.warning("No prices found on any site.")

