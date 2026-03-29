import streamlit as st
import pandas as pd
import os
import sys
import plotly.express as px
import plotly.graph_objects as go

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

st.title("🕸️ LinkedIn Virality & Breakthrough Analysis")
st.markdown("Analyze post resonance beyond your company and network circles.")

with st.sidebar:
    st.header("1. Credentials (Local)")
    st.markdown("We use Browser Automation via Playwright. Enter your LinkedIn credentials below:")
    
    email_input = st.text_input("LinkedIn Email", value=os.getenv("LINKEDIN_EMAIL", ""))
    pass_input = st.text_input("LinkedIn Password", value=os.getenv("LINKEDIN_PASSWORD", ""), type="password")
    
    if email_input and pass_input:
        os.environ["LINKEDIN_EMAIL"] = email_input
        os.environ["LINKEDIN_PASSWORD"] = pass_input
    
    st.header("2. Search Parameters")
    limit_posts = st.number_input("Number of posts to scrape", min_value=1, max_value=20, value=10)
    limit_reactions = st.number_input("Max reactions per post", min_value=10, max_value=500, value=100)
        
    st.header("3. Target Profile")
    target_url = st.text_input("LinkedIn Profile URL", placeholder="https://www.linkedin.com/in/williamhgates/")
    author_company = st.text_input("Author's Company (e.g. IBM, Microsoft)", value="Unknown")
    debug_mode = st.checkbox("Show Browser (Debug Mode)", value=False, help="Check this if you hit a CAPTCHA or want to watch the scraper.")
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
                run_pipeline(target_url, author_company=author_company, limit_posts=limit_posts, limit_reactions=limit_reactions, headless=not debug_mode)
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
    try:
        df = pd.read_csv(RESULTS_FILE)
        if not df.empty:
            st.subheader("📊 Resonance & Breakthrough KPI")
            
            # Global Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            # Internal vs External
            author_comp = df["Author Company"].iloc[0] if "Author Company" in df.columns else "Unknown"
            df["Engagement Type"] = df["Reactor Company/Headline"].apply(lambda x: "Internal" if str(author_comp).lower() in str(x).lower() else "External")
            
            external_count = len(df[df["Engagement Type"] == "External"])
            resonance_pct = (external_count / len(df)) * 100 if len(df) > 0 else 0
            
            col1.metric("Total Reactions", len(df))
            col2.metric("External Resonance", f"{resonance_pct:.1f}%")
            col3.metric("Total Posts", df["Post URL"].nunique())
            col4.metric("Avg Virality Score", f"{df['Virality Score'].mean():.2f}")
            
            # Visualizations Row
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("#### Breakthrough: Internal vs External")
                fig_break = px.pie(df, names="Engagement Type", color="Engagement Type", 
                                  color_discrete_map={"Internal": "#FF4B4B", "External": "#1f77b4"},
                                  hole=0.4)
                st.plotly_chart(fig_break, use_container_width=True)
                
            with c2:
                st.markdown("#### Reaction Distance (Connection Degree)")
                # Normalize degrees for sorting
                order = ["1st", "2nd", "3rd", "Out"]
                deg_counts = df["Connection Degree"].value_counts().reset_index()
                deg_counts.columns = ["Degree", "Count"]
                fig_deg = px.bar(deg_counts, x="Degree", y="Count", color="Degree", 
                               category_orders={"Degree": order},
                               color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_deg, use_container_width=True)
            
            st.markdown("---")
            
            # Post Specific Analysis
            st.subheader("🎯 Post-Specific Deep Dive")
            post_urls = df["Post URL"].unique()
            selected_post_url = st.selectbox("Select a Post to Analyze", post_urls)
            
            post_df = df[df["Post URL"] == selected_post_url]
            st.info(f"**Post Content Snippet:** {post_df['Post Text'].iloc[0]}")
            
            pcol1, pcol2 = st.columns([1, 2])
            with pcol1:
                p_external = len(post_df[post_df["Engagement Type"] == "External"])
                p_resonance = (p_external / len(post_df)) * 100 if len(post_df) > 0 else 0
                st.metric("Post Resonance", f"{p_resonance:.1f}%")
                
                # Gauge Chart for Resonance
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = p_resonance,
                    title = {'text': "External Resonance %"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "#1f77b4"},
                        'steps': [
                            {'range': [0, 30], 'color': "lightgray"},
                            {'range': [30, 70], 'color': "gray"},
                            {'range': [70, 100], 'color': "lightblue"}],
                    }
                ))
                fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)

            with pcol2:
                st.markdown("#### Top Engaging External Companies / Titles")
                external_df = post_df[post_df["Engagement Type"] == "External"]
                if not external_df.empty:
                    top_comps = external_df["Reactor Company/Headline"].value_counts().head(10).reset_index()
                    top_comps.columns = ["Company/Headline", "Reactions"]
                    fig_comp = px.bar(top_comps, y="Company/Headline", x="Reactions", orientation='h', color="Reactions")
                    st.plotly_chart(fig_comp, use_container_width=True)
                else:
                    st.warning("No external engagement found for this post yet.")

            st.markdown("---")
            st.subheader("🕸️ Virtual Connection Map")
            render_network(post_df)
            
            with st.expander("Show Raw Data Table"):
                st.dataframe(df, use_container_width=True)
                with open(RESULTS_FILE, "rb") as file:
                    st.download_button("Download Full CSV", data=file, file_name="virality_results.csv", mime="text/csv")
        else:
            st.info("No data inside the results file.")
    except Exception as e:
         st.error(f"Error reading {RESULTS_FILE}: {e}")
         st.exception(e)
else:
    st.info("Run the pipeline to generate data.")
