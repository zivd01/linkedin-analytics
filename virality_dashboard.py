import streamlit as st
import pandas as pd
import os
import sys

# Ensure we can import our pipeline
from virality_pipeline import main as run_pipeline

# Attempt to load PyVis for the interactive map
try:
    from pyvis.network import Network
    import streamlit.components.v1 as components
    HAS_PYVIS = True
except ImportError:
    HAS_PYVIS = False

st.set_page_config(page_title="LinkedIn Playwright Scraper", page_icon="🕸️", layout="wide")

st.title("🕸️ LinkedIn Virality Pipeline Dashboard")
st.markdown("Run the Playwright Scraper on a specific LinkedIn Profile URL.")

with st.sidebar:
    st.header("1. Credentials (Local)")
    st.markdown("We use Browser Automation via Playwright. Please ensure `.env` is configured or enter below:")
    
    email_input = st.text_input("LinkedIn Email", value=os.getenv("LINKEDIN_EMAIL", ""))
    pass_input = st.text_input("LinkedIn Password", value=os.getenv("LINKEDIN_PASSWORD", ""), type="password")
    
    if email_input and pass_input:
        os.environ["LINKEDIN_EMAIL"] = email_input
        os.environ["LINKEDIN_PASSWORD"] = pass_input
        
    st.header("2. Target Profile")
    target_url = st.text_input("LinkedIn Profile URL", placeholder="https://www.linkedin.com/in/williamhgates/")
    run_button = st.button("Run Pipeline 🚀")

st.markdown("---")

RESULTS_FILE = "virality_results.csv"

def render_network(df):
    if not HAS_PYVIS:
        st.warning("PyVis is not installed. Run `pip install pyvis networkx` for the interactive map.")
        return
        
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.force_atlas_2based()
    
    # Add Author Node
    authors = df["Author Name"].dropna().unique()
    for auth in authors:
        net.add_node(auth, label=auth, size=30, color="#FF4B4B", title="Post Author")
        
    # Add Reactor Nodes and Edges
    for _, row in df.iterrows():
        reactor = row["Reactor Name"]
        author = row["Author Name"]
        score = row["Virality Score"]
        degree = row["Connection Degree"]
        
        if pd.isna(reactor) or pd.isna(author): continue
        
        color = "#1f77b4" if score == 1 else "#ff7f0e" if score == 3 else "#2ca02c"
        net.add_node(reactor, label=reactor, size=15, color=color, title=f"{reactor} ({degree})")
        net.add_edge(author, reactor, value=score, title=f"Distance: {degree}")

    net.save_graph("virality_network.html")
    with open("virality_network.html", "r", encoding="utf-8") as f:
        html_data = f.read()
    components.html(html_data, height=650)

if run_button:
    if not target_url.startswith("http"):
        st.error("Please provide a valid LinkedIn Profile URL starting with https://")
    elif not email_input or not pass_input:
        st.error("Please provide your LinkedIn credentials to allow the scraper to log in.")
    else:
        with st.spinner("Extracting posts and reactions... Since we pause 30s per post, this will take ~5 minutes."):
            import sys
            import io
            old_stdout = sys.stdout
            mystdout = io.StringIO()
            sys.stdout = mystdout
            
            try:
                run_pipeline(target_url)
                st.success("Pipeline Execution Finished!")
            except Exception as e:
                st.error(f"Pipeline Error: {e}")
            finally:
                sys.stdout = old_stdout
                logs = mystdout.getvalue()
                with st.expander("Show Console Logs"):
                     st.text(logs)

# Display Results
if os.path.exists(RESULTS_FILE):
    st.subheader("📊 Extraction Results")
    try:
        df = pd.read_csv(RESULTS_FILE)
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Reactions", len(df))
            col2.metric("Total Posts Found", df["Post URL"].nunique())
            avg_score = df["Virality Score"].mean()
            col3.metric("Avg Virality Score", f"{avg_score:.2f}")
            
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🕸️ Interactive Virality Map")
            render_network(df)
            
            st.markdown("### ☁️ Export to Kumu.io")
            with open(RESULTS_FILE, "rb") as file:
                btn = st.download_button("Download virality_results.csv", data=file, file_name="virality_results.csv", mime="text/csv")
        else:
            st.info("No data inside the results file.")
    except Exception as e:
         st.error(f"Error reading {RESULTS_FILE}: {e}")
else:
    st.info("Run the pipeline to generate data.")
