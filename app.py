import streamlit as st
import requests
from bs4 import BeautifulSoup
import numpy as np
import openai
import time

# ----------------------------
# STREAMLIT CONFIG
# ----------------------------
st.set_page_config(page_title="Barcode Price Intelligence", layout="centered")
st.title("📦 Barcode-based Multi-Market Price Intelligence")
st.caption("Enter a product barcode (EAN/GTIN) to find prices on Ceneo, Allegro, Amazon, and Google Shopping.")

# ----------------------------
# OPENAI CONFIG
# ----------------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ----------------------------
# SCRAPER HELPERS
# ----------------------------
def safe_float(text):
    """Convert PLN string price to float safely."""
    text = text.replace("zł", "").replace(",", ".").replace(" ", "")
    return float(text)

# ----------------------------
# MARKETPLACE SCRAPERS
# ----------------------------
def scrape_ceneo(ean):
    url = f"https://www.ceneo.pl/;szukaj-{ean}"
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for el in soup.select(".price"):
        try:
            prices.append(safe_float(el.get_text(strip=True)))
        except:
            continue
    return prices

def scrape_allegro(ean):
    url = f"https://allegro.pl/listing?string={ean}"
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for el in soup.select("span._9c44d_1zemI span"):
        try:
            prices.append(safe_float(el.get_text(strip=True)))
        except:
            continue
    return prices

def scrape_amazon(ean):
    url = f"https://www.amazon.pl/s?k={ean}"
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for el in soup.select("span.a-price-whole"):
        try:
            prices.append(safe_float(el.get_text(strip=True)))
        except:
            continue
    return prices

def scrape_google_shopping(ean):
    url = f"https://www.google.com/search?tbm=shop&q={ean}"
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
def aggregate_prices(ean):
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
            prices = fn(ean)
            results[site] = prices
            time.sleep(1)
        except Exception as e:
            st.warning(f"{site} error: {e}")
            results[site] = []
    all_prices = [p for site_prices in results.values() for p in site_prices]
    return all_prices, {site: len(p) for site, p in results.items()}

# ----------------------------
# GPT SUMMARY
# ----------------------------
def gpt_summary(ean, median, deviation, site_counts):
    prompt = f"""
Product EAN: {ean}
Median Market Price: {median:.2f} zł
Deviation: {deviation:.1f}%
Listings found per site: {site_counts}

Summarize this pricing situation briefly in a professional business tone.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-5",  # or "gpt-4-turbo"
            messages=[{"role": "user", "content": prompt}],
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"GPT Error: {e}")
        return None

# ----------------------------
# STREAMLIT INTERFACE
# ----------------------------
barcode = st.text_input("🔢 Enter product barcode (EAN):", key="barcode_input")
rrp = st.number_input("💰 Enter your recommended retail price (RRP) in zł:", min_value=0.0, step=0.01)

if st.button("Check Market Prices", key="search_btn"):
    if not barcode:
        st.warning("Please enter a product barcode.")
        st.stop()

    with st.spinner("Scraping marketplaces..."):
        all_prices, site_counts = aggregate_prices(barcode)

    if all_prices:
        median = np.median(all_prices)
        deviation = (median - rrp) / rrp * 100 if rrp else 0

        st.metric("Median Market Price", f"{median:.2f} zł")
        st.metric("Deviation vs RRP", f"{deviation:.1f}%")
        st.write("🛍️ Listings found per site:", site_counts)
        st.bar_chart(all_prices)

        with st.spinner("Generating GPT summary..."):
            summary = gpt_summary(barcode, median, deviation, site_counts)
        if summary:
            st.markdown("### 🧠 GPT Summary")
            st.write(summary)
    else:
        st.warning("No prices found for this barcode.")


