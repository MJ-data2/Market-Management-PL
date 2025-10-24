# 💰 Market Price Intelligence Dashboard

This app scrapes product pages from your website and compares their prices against Ceneo.pl marketplace data to find the median market price.  
It then uses GPT to generate natural-language summaries of price deviations.

---

### 🧩 Features
- Scrapes your product URL for RRP and SKU info
- Searches Ceneo.pl for similar listings
- Calculates the median market price
- Uses GPT to summarize results in plain language
- Built entirely with HTML scraping (no APIs)

---

### ⚙️ Tech Stack
- **Frontend:** Streamlit
- **Scraping:** BeautifulSoup + Requests
- **AI Analysis:** OpenAI GPT
- **Hosting:** Streamlit Cloud (free tier)

---

### 🚀 How to Deploy
1. Push these files to your GitHub repository.
2. Go to [Streamlit Cloud](https://share.streamlit.io/).
3. Click **"New app"**, select your repo, and choose `app.py` as the entry point.
4. Add your OpenAI API key under **Settings → Secrets**:

5. Deploy — Streamlit will automatically install dependencies and launch your dashboard.

---

### 🧠 Example Usage
Enter your product page URL, and the app will:
1. Scrape the RRP from your site.
2. Scrape Ceneo.pl for market prices.
3. Calculate the median market price.
4. Display deviation vs RRP.
5. Generate a GPT summary.

