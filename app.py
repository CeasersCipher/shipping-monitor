"""Streamlit dashboard for shipping rate monitoring."""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

from storage import StorageManager
from scheduler import init_scheduler, get_scheduler
from config import PACKAGES, ROUTES, SCRAPE_INTERVAL_SECONDS
from scrapers import use_live_rates, get_live_rate_provider

# Page configuration
st.set_page_config(
    page_title="Shipping Rate Monitor",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-refresh every 5 minutes (300000 ms)
st_autorefresh(interval=300000, key="data_refresh")

# Initialize storage
storage = StorageManager()

# Initialize scheduler (runs in background)
if "scheduler_initialized" not in st.session_state:
    scheduler = init_scheduler(
        storage=storage,
        interval_seconds=SCRAPE_INTERVAL_SECONDS,
        run_immediately=True
    )
    st.session_state.scheduler_initialized = True
    st.session_state.scheduler = scheduler
else:
    scheduler = get_scheduler()


def format_price(price: float, currency: str = "USD") -> str:
    """Format price for display."""
    if currency == "USD":
        return f"${price:.2f}"
    return f"{price:.2f} {currency}"


def get_current_rates_df() -> pd.DataFrame:
    """Get current rates as a DataFrame."""
    latest_rates = storage.get_latest_rates()

    if not latest_rates:
        return pd.DataFrame()

    data = []
    for rate in latest_rates.values():
        data.append({
            "Carrier": rate.carrier,
            "Service": rate.service,
            "Package": rate.package_name,
            "Route": f"{rate.origin} → {rate.destination}",
            "Price": rate.price,
            "Currency": rate.currency,
            "Delivery Days": rate.delivery_days or "N/A",
            "Last Updated": rate.timestamp,
        })

    return pd.DataFrame(data)


def get_changes_df() -> pd.DataFrame:
    """Get recent rate changes as a DataFrame."""
    changes = storage.get_all_changes(limit=50)

    if not changes:
        return pd.DataFrame()

    data = []
    for change in changes:
        data.append({
            "Carrier": change.rate.carrier,
            "Service": change.rate.service,
            "Package": change.rate.package_name,
            "Route": f"{change.rate.origin} → {change.rate.destination}",
            "Old Price": change.old_price,
            "New Price": change.new_price,
            "Change": change.change_amount,
            "Change %": change.change_percent,
            "Detected At": change.detected_at,
        })

    return pd.DataFrame(data)


# Sidebar
with st.sidebar:
    st.title("📦 Rate Monitor")
    st.markdown("---")

    # Data source status
    st.subheader("Data Source")
    if use_live_rates():
        provider = get_live_rate_provider()
        st.success(f"🟢 Live Rates ({provider})")
        st.caption("Real-time carrier rates")
    else:
        st.warning("🟡 Estimated Rates")
        st.caption("Using rate estimates")
        with st.expander("Enable Live Rates"):
            st.markdown("""
            **Get real carrier rates:**

            **Option 1: Shippo** (Recommended)
            1. Sign up at [goshippo.com](https://goshippo.com)
            2. Get API key from dashboard
            3. Run: `SHIPPO_API_KEY=xxx ./run.sh`

            **Option 2: EasyPost**
            1. Sign up at [easypost.com](https://www.easypost.com)
            2. Get API key from dashboard
            3. Run: `EASYPOST_API_KEY=xxx ./run.sh`
            """)

    st.markdown("---")

    # Status section
    st.subheader("Status")
    status = scheduler.get_status()

    if status["is_running"]:
        st.success("🟢 Scheduler Running")
    else:
        st.error("🔴 Scheduler Stopped")

    if status["last_run"]:
        last_run = datetime.fromisoformat(status["last_run"])
        st.metric("Last Scrape", last_run.strftime("%H:%M:%S"))

    if status["next_run"]:
        next_run = datetime.fromisoformat(status["next_run"])
        time_until = next_run - datetime.now(next_run.tzinfo)
        minutes = int(time_until.total_seconds() / 60)
        st.metric("Next Scrape", f"in {minutes} min")

    st.markdown("---")

    # Manual refresh button
    if st.button("🔄 Refresh Now", use_container_width=True):
        scheduler.run_now()
        st.success("Scrape triggered!")
        st.rerun()

    st.markdown("---")

    # Filters
    st.subheader("Filters")

    rates_df = get_current_rates_df()

    if not rates_df.empty:
        carriers = ["All"] + sorted(rates_df["Carrier"].unique().tolist())
        selected_carrier = st.selectbox("Carrier", carriers)

        packages = ["All"] + sorted(rates_df["Package"].unique().tolist())
        selected_package = st.selectbox("Package Size", packages)
    else:
        selected_carrier = "All"
        selected_package = "All"


# Main content
st.title("📦 Shipping Rate Monitor")

# Data source banner
if use_live_rates():
    provider = get_live_rate_provider()
    st.success(f"**Live Rates Active** - Real-time rates from UPS, USPS, FedEx, DHL via {provider} API")
else:
    st.info("**Demo Mode** - Showing estimated rates. Set SHIPPO_API_KEY or EASYPOST_API_KEY for live rates")

st.markdown("Track shipping rates across carriers in real-time")

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Current Rates", "📈 Rate History", "🔔 Rate Changes", "ℹ️ Status"])

with tab1:
    st.header("Current Shipping Rates")

    rates_df = get_current_rates_df()

    if rates_df.empty:
        st.info("No rate data available yet. The scraper will run shortly...")
    else:
        # Apply filters
        filtered_df = rates_df.copy()

        if selected_carrier != "All":
            filtered_df = filtered_df[filtered_df["Carrier"] == selected_carrier]

        if selected_package != "All":
            filtered_df = filtered_df[filtered_df["Package"] == selected_package]

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Rates", len(filtered_df))

        with col2:
            carriers_count = filtered_df["Carrier"].nunique()
            st.metric("Carriers", carriers_count)

        with col3:
            if not filtered_df.empty:
                avg_price = filtered_df["Price"].mean()
                st.metric("Avg Price", f"${avg_price:.2f}")

        with col4:
            if not filtered_df.empty:
                min_price = filtered_df["Price"].min()
                st.metric("Lowest Rate", f"${min_price:.2f}")

        st.markdown("---")

        # Rate comparison by carrier and service
        st.subheader("Rate Comparison")

        for package in PACKAGES:
            if selected_package != "All" and selected_package != package.name:
                continue

            package_df = filtered_df[filtered_df["Package"] == package.name]

            if package_df.empty:
                continue

            st.markdown(f"**{package.name} Package** ({package.dimensions_str}\", {package.weight} lb)")

            # Create comparison chart
            fig = px.bar(
                package_df.sort_values("Price"),
                x="Service",
                y="Price",
                color="Carrier",
                title=f"{package.name} Package Rates",
                barmode="group",
                hover_data=["Delivery Days", "Route"]
            )
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Full data table
        st.subheader("All Rates")

        display_df = filtered_df.copy()
        display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:.2f}")

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Last Updated": st.column_config.DatetimeColumn(
                    "Last Updated",
                    format="MMM DD, HH:mm"
                )
            }
        )


with tab2:
    st.header("Rate History")

    # Get historical data
    historical = storage.get_historical_rates(days=30)

    if not historical:
        st.info("No historical data available yet. Check back after a few scraping cycles.")
    else:
        # Build time series data
        time_series_data = []

        for entry in historical:
            for rate_data in entry.get("rates", []):
                time_series_data.append({
                    "Timestamp": entry["timestamp"],
                    "Carrier": rate_data["carrier"],
                    "Service": rate_data["service"],
                    "Package": rate_data["package_name"],
                    "Price": rate_data["price"],
                    "Route": f"{rate_data['origin']} → {rate_data['destination']}"
                })

        if time_series_data:
            ts_df = pd.DataFrame(time_series_data)
            ts_df["Timestamp"] = pd.to_datetime(ts_df["Timestamp"])

            # Filter options
            col1, col2 = st.columns(2)

            with col1:
                hist_carriers = ["All"] + sorted(ts_df["Carrier"].unique().tolist())
                hist_carrier = st.selectbox("Select Carrier", hist_carriers, key="hist_carrier")

            with col2:
                hist_packages = ["All"] + sorted(ts_df["Package"].unique().tolist())
                hist_package = st.selectbox("Select Package", hist_packages, key="hist_package")

            filtered_ts = ts_df.copy()

            if hist_carrier != "All":
                filtered_ts = filtered_ts[filtered_ts["Carrier"] == hist_carrier]

            if hist_package != "All":
                filtered_ts = filtered_ts[filtered_ts["Package"] == hist_package]

            if not filtered_ts.empty:
                # Create line chart
                fig = px.line(
                    filtered_ts,
                    x="Timestamp",
                    y="Price",
                    color="Service",
                    title="Rate History Over Time",
                    markers=True,
                    hover_data=["Carrier", "Package", "Route"]
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

                # Show data table
                st.subheader("Historical Data")
                st.dataframe(
                    filtered_ts.sort_values("Timestamp", ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No data matching the selected filters.")
        else:
            st.info("No time series data available.")


with tab3:
    st.header("Rate Changes")

    changes_df = get_changes_df()

    if changes_df.empty:
        st.info("No rate changes detected yet. Changes will appear here when prices update.")
    else:
        # Summary
        col1, col2, col3 = st.columns(3)

        with col1:
            total_changes = len(changes_df)
            st.metric("Total Changes", total_changes)

        with col2:
            increases = len(changes_df[changes_df["Change"] > 0])
            st.metric("Price Increases", increases, delta=f"{increases}", delta_color="inverse")

        with col3:
            decreases = len(changes_df[changes_df["Change"] < 0])
            st.metric("Price Decreases", decreases, delta=f"{decreases}", delta_color="normal")

        st.markdown("---")

        # Changes table with color coding
        st.subheader("Recent Changes")

        def style_change(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return "color: red"
                elif val < 0:
                    return "color: green"
            return ""

        display_changes = changes_df.copy()
        display_changes["Old Price"] = display_changes["Old Price"].apply(lambda x: f"${x:.2f}")
        display_changes["New Price"] = display_changes["New Price"].apply(lambda x: f"${x:.2f}")
        display_changes["Change"] = display_changes["Change"].apply(lambda x: f"${x:+.2f}")
        display_changes["Change %"] = display_changes["Change %"].apply(lambda x: f"{x:+.1f}%")

        st.dataframe(
            display_changes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Detected At": st.column_config.DatetimeColumn(
                    "Detected At",
                    format="MMM DD, HH:mm"
                )
            }
        )

        # Change distribution chart
        st.subheader("Change Distribution by Carrier")

        changes_by_carrier = changes_df.groupby("Carrier")["Change"].agg(["count", "mean"]).reset_index()
        changes_by_carrier.columns = ["Carrier", "Count", "Avg Change"]

        fig = px.bar(
            changes_by_carrier,
            x="Carrier",
            y="Count",
            color="Avg Change",
            title="Rate Changes by Carrier",
            color_continuous_scale=["green", "yellow", "red"],
            color_continuous_midpoint=0
        )
        st.plotly_chart(fig, use_container_width=True)


with tab4:
    st.header("System Status")

    status = scheduler.get_status()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Scheduler Status")

        st.markdown(f"**Running:** {'✅ Yes' if status['is_running'] else '❌ No'}")
        st.markdown(f"**Interval:** {status['interval_seconds'] // 60} minutes")

        if status["last_run"]:
            last_run = datetime.fromisoformat(status["last_run"])
            st.markdown(f"**Last Run:** {last_run.strftime('%Y-%m-%d %H:%M:%S')}")

        if status["next_run"]:
            next_run = datetime.fromisoformat(status["next_run"])
            st.markdown(f"**Next Run:** {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    with col2:
        st.subheader("Storage Status")

        storage_status = storage.get_scrape_status()

        st.markdown(f"**Total Rates Stored:** {storage_status['total_rates']}")
        st.markdown(f"**Carriers:** {', '.join(storage_status['carriers']) or 'None'}")

        if storage_status["last_scrape"]:
            last = datetime.fromisoformat(storage_status["last_scrape"])
            st.markdown(f"**Last Data:** {last.strftime('%Y-%m-%d %H:%M:%S')}")

    st.markdown("---")

    # Last scrape results
    st.subheader("Last Scrape Results")

    if status["last_results"]:
        for result in status["last_results"]:
            with st.expander(f"{result['carrier']} - {'✅ Success' if result['success'] else '❌ Failed'}"):
                st.markdown(f"**Timestamp:** {result['timestamp']}")
                st.markdown(f"**Rates Retrieved:** {len(result['rates'])}")
                if result["error"]:
                    st.error(f"Error: {result['error']}")
    else:
        st.info("No scrape results yet. The first scrape should complete shortly.")

    st.markdown("---")

    # Configuration
    st.subheader("Configuration")

    st.markdown("**Tracked Packages:**")
    for pkg in PACKAGES:
        st.markdown(f"- {pkg.name}: {pkg.dimensions_str}\", {pkg.weight} lb")

    st.markdown("**Tracked Routes:**")
    for route in ROUTES:
        st.markdown(f"- {route.name}: {route.origin_zip} ({route.origin_country}) → {route.destination_zip} ({route.destination_country})")


# Footer
st.markdown("---")
if use_live_rates():
    provider = get_live_rate_provider()
    st.caption(f"Shipping Rate Monitor | Live rates via {provider} API | Scraped hourly")
else:
    st.caption("Shipping Rate Monitor | Estimated rates (Demo Mode) | Set SHIPPO_API_KEY for live rates")
