---
description: Start the 3-step LinkedIn Virality analysis Dashboard (Local PC Scraper).
---

# LinkedIn Virality Dashboard
This tool uses your local environment to scrape LinkedIn data by logging in as your user.
We **highly recommend** populating your `.env` file first:
```bash
echo "LINKEDIN_EMAIL=your.email@gmail.com" >> c:\Users\823162756\Documents\GitHub\linkedin-analytics\.env
echo "LINKEDIN_PASSWORD=your_password" >> c:\Users\823162756\Documents\GitHub\linkedin-analytics\.env
```
(Alternatively, you can type these credentials directly into the UI).

# Execution Steps
// turbo
1. Start the UI:
   ```bash
   python -m streamlit run c:\Users\823162756\Documents\GitHub\linkedin-analytics\virality_dashboard.py
   ```

2. Open the URL provided in the terminal (usually http://localhost:8501).
3. Enter the LinkedIn Profile URL (e.g. `https://www.linkedin.com/in/williamhgates/`).
4. Click "Run Pipeline". 
5. The scraper will open a hidden browser, log in, navigate to the target URL, scroll through their latest posts, and extract the reactions. **This takes several minutes** due to a built-in 30-second delay between posts to protect your account.
6. The dashboard will automatically refresh to show the interactive PyVis map and metrics.
