#!/bin/bash
# Shipping Rate Monitor - Run Script
#
# For live rates, get an API key from https://www.easypost.com
# Sign up is free, API key works immediately
#
# Usage:
#   ./run.sh                          # Run with estimated rates (demo)
#   EASYPOST_API_KEY=xxx ./run.sh     # Run with live rates

cd "$(dirname "$0")"

echo "========================================="
echo "   Shipping Rate Monitor"
echo "========================================="

if [ -n "$EASYPOST_API_KEY" ]; then
    echo "Mode: LIVE RATES (EasyPost API)"
    echo "Carriers: UPS, USPS, FedEx, DHL + more"
else
    echo "Mode: DEMO (Estimated rates)"
    echo ""
    echo "To enable live rates:"
    echo "  1. Sign up at https://www.easypost.com"
    echo "  2. Get API key from dashboard"
    echo "  3. Run: EASYPOST_API_KEY=your_key ./run.sh"
fi

echo "========================================="
echo ""

streamlit run app.py
