import streamlit as st
import requests
from bs4 import BeautifulSoup
import numpy as np
import time
import random
import plotly.express as px
from openai import OpenAI

# ----------------------------
# STREAMLIT CONFIG
# ----------------------------
st.set_page_config(page_title="Universal Price Intelligence", layout="centered")
st.title(" Universal Multi-Market Price Intelligence Dashboard")
st.caption("Compare Ceneo, Allegro, Amazon, and Google Shopping prices by barcode (EAN), convert to EUR, and summarize with GPT.")

# ----------------------------
# API KEYS
# ----------------------------
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
SCRAPER_API_KEY = st.secrets["SCRAPER_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Accept-Language": "pl,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Connection": "keep-alive",
}

# ----------------------------
# CURRENCY CONVERSION
# ----------------------------
def get_exchange_rate_pln_to_eur():
    """Fetch live PLN→EUR rate with fallback."""
    try:
        res = requests.get("https://api.exchangerate.host/latest?base=PLN&symbols=EUR", timeout=10)
        data = res.json()
        return float(data["rates"]["EUR"])
    except Exception:
        return 0.23  # fallback rate if API fails

# ----------------------------
# SCRAPER HELPERS
# ----------------------------
def safe_float(text):
    """Convert PLN string price to float safely."""
    text = text.replace("zł", "").replace(",", ".").replace(" ", "")
    try:
        return float(text)
    except:
        return None

def get_html(url, retries=3):
    """Get rendered HTML using ScraperAPI with retries, scroll and longer wait."""
    for attempt in range(retries):
        try:
            proxy_url = (
                f"https://api.scraperapi.com?"
                f"api_key={SCRAPER_API_KEY}"
                f"&render=true&render_scroll=true"
                f"&country_code=pl&render_wait=8&url={url}"
            )
            res = requests.get(proxy_url, headers=HEADERS, timeout=90)
            res.raise_for_status()
            return res.text
        except Exception as e:
            st.warning(f"ScraperAPI attempt {attempt+1} failed for {url[:60]}... ({e})")
            time.sleep(3)
    return ""

# ----------------------------
# MARKETPLACE SCRAPERS
# ----------------------------
def scrape_ceneo(ean):
    url = f"https://www.ceneo.pl/;szukaj-{ean}"
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    results = []

    product_cards = soup.select("div.cat-prod-row")
    for card in product_cards:
        try:
            price_el = card.select_one(".price, .price-value")
            seller_el = card.select_one(".shop-name, .product-offer-link")
            if price_el:
                price = safe_float(price_el.get_text(strip=True))
                if price is not None:
                    seller = seller_el.get_text(strip=True) if seller_el else "Unknown seller"
                    results.append({"seller": seller, "price": price})
        except Exception:
            continue
    return results


def scrape_allegro(ean):
    url = f"https://allegro.pl/listing?string={ean}"
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("article[data-role='offer']"):
        try:
            price_el = card.select_one("span._9c44d_3AMmE")
            seller_el = card.select_one("div._9c44d_3N42J span")
            if price_el:
                price = safe_float(price_el.get_text(strip=True))
                if price is not None:
                    seller = seller_el.get_text(strip=True) if seller_el else "Unknown seller"
                    results.append({"seller": seller, "price": price})
        except Exception:
            continue
    return results


def scrape_amazon(ean):
    url = f"https://www.amazon.pl/s?k={ean}"
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("div.s-result-item[data-component-type='s-search-result']"):
        try:
            price_el = card.select_one("span.a-price span.a-offscreen")
            seller_el = card.select_one("h5.s-line-clamp-1, span.a-size-small.a-color-secondary")
            if price_el:
                price = safe_float(price_el.get_text(strip=True))
                if price is not None:
                    seller = seller_el.get_text(strip=True) if seller_el else "Unknown seller"
                    results.append({"seller": seller, "price": price})
        except Exception:
            continue
    return results


def scrape_google_shopping(ean):
    url = f"https://www.google.com/search?tbm=shop&hl=pl&gl=pl&q={ean}"
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select("div.sh-dgr__grid-result, div.sh-pr__product-results"):
        try:
            price_el = card.select_one("span.a8Pemb, span.T14wmb")
            seller_el = card.select_one("div.aULzUe, div.E5ocAb")
            if price_el:
                price = safe_float(price_el.get_text(strip=True))
                if price is not None:
                    seller = seller_el.get_text(strip=True) if seller_el else "Unknown seller"
                    results.append({"seller": seller, "price": price})
        except Exception:
            continue
    return results

# ----------------------------
# AGGREGATOR
# ----------------------------
def aggregate_prices(ean):
    """Collect prices from all supported sites using ScraperAPI."""
    results = {}
    for site, fn in {
        "Ceneo": scrape_ceneo,
        "Allegro": scrape_allegro,
        "Amazon": scrape_amazon,
        "Google": scrape_google_shopping,
    }.items():
        try:
            st.write(f"🔍 Searching **{site}** ...")
            data = fn(ean)
            results[site] = data
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            st.warning(f"{site} error: {e}")
            results[site] = []
    all_prices = []
    for site, site_data in results.items():
        if site_data:
            if isinstance(site_data[0], dict):
                all_prices.extend([item["price"] for item in site_data])
            else:
                all_prices.extend(site_data)
    return all_prices, {site: len(p) for site, p in results.items()}, results

# ----------------------------
# GPT SUMMARY
# ----------------------------
def gpt_summary(ean, median, deviation, site_counts, currency_symbol):
    prompt = f"""
Product EAN: {ean}
Median Market Price: {median:.2f} {currency_symbol}
Deviation vs RRP: {deviation:.1f}%
Listings per site: {site_counts}

Provide a short professional summary comparing market prices to RRP.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"GPT Error: {e}")
        return None

# ----------------------------
# STREAMLIT INTERFACE
# ----------------------------
barcode = st.text_input("🔢 Enter product barcode (EAN):", key="barcode_input")
rrp = st.number_input("💰 Enter your recommended retail price (RRP) in zł:", min_value=0.0, step=0.01)
currency = st.radio("🌍 Display prices in:", ["PLN", "EUR"], horizontal=True)

if st.button("Check Market Prices", key="search_btn"):
    if not barcode:
        st.warning("Please enter a product barcode.")
        st.stop()

    with st.spinner("Scraping marketplaces..."):
        all_prices, site_counts, site_data = aggregate_prices(barcode)

    if all_prices:
        median = np.median(all_prices)
        deviation = (median - rrp) / rrp * 100 if rrp else 0

        # Currency conversion
        rate = 1.0
        symbol = "zł"
        if currency == "EUR":
            rate = get_exchange_rate_pln_to_eur()
            symbol = "€"

        median_converted = median * rate
        rrp_converted = rrp * rate if rrp else 0

        st.metric("Median Market Price", f"{median_converted:.2f} {symbol}")
        st.metric("Deviation vs RRP", f"{deviation:.1f}%")
        st.write("🛍️ Listings found per site:", site_counts)

        # ---------- Chart Section ----------
        for site, data in site_data.items():
            if data and isinstance(data[0], dict):
                df = [{"Seller": item["seller"], "Price": item["price"] * rate} for item in data]
                fig = px.bar(
                    df,
                    x="Seller",
                    y="Price",
                    text="Price",
                    title=f"{site} Seller Prices ({symbol})",
                    labels={"Price": f"Price ({symbol})", "Seller": "Seller"},
                )
                fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig.update_yaxes(title_text=f"Price in {symbol}")
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

        # ---------- Table Section ----------
        st.markdown("### 📊 Per-Site Price Summary")
        table_data = []
        for site, prices in site_data.items():
            if prices:
                if isinstance(prices[0], dict):
                    site_prices = [p["price"] for p in prices]
                else:
                    site_prices = prices
                table_data.append({
                    "Site": site,
                    "Count": len(site_prices),
                    "Min": f"{min(site_prices) * rate:.2f} {symbol}",
                    "Median": f"{np.median(site_prices) * rate:.2f} {symbol}",
                    "Max": f"{max(site_prices) * rate:.2f} {symbol}"
                })
        if table_data:
            st.dataframe(table_data, use_container_width=True)
        else:
            st.write("No per-site data to show.")

        # ---------- GPT Summary ----------
        with st.spinner("Generating GPT summary..."):
            summary = gpt_summary(barcode, median_converted, deviation, site_counts, symbol)
        if summary:
            st.markdown("### 🧠 GPT Summary")
            st.write(summary)
    else:
        st.warning("No prices found for this barcode.")





