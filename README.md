# Shipping Rate Monitor

Real-time shipping rate tracking across major carriers (UPS, USPS, FedEx, DHL).

![Dashboard](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)

## Features

- **Live Rate Tracking** - Real-time rates via Shippo or EasyPost API
- **Multi-Carrier Support** - UPS, USPS, FedEx, DHL Express
- **Rate Change Detection** - Alerts when prices change
- **Historical Charts** - Track rate trends over time
- **Hourly Updates** - Automatic background scraping

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with live rates (recommended)
SHIPPO_API_KEY=your_key streamlit run app.py

# Or run in demo mode (estimated rates)
streamlit run app.py
```

## Getting Live Rates

Sign up for a free API key:
- **Shippo** (recommended): [goshippo.com](https://goshippo.com) - Free tier, instant setup
- **EasyPost**: [easypost.com](https://www.easypost.com) - Free tier available

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add your API key in Secrets:
   ```toml
   SHIPPO_API_KEY = "your_key_here"
   ```

## Configuration

Edit `config.py` to customize:
- Package sizes to track
- Shipping routes
- Scrape interval

## License

MIT
