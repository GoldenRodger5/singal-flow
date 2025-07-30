# Streamlit Cloud Deployment Guide

## Quick Deployment to Streamlit Cloud

### 1. Prepare for Deployment
- Ensure your enhanced dashboard is in `enhanced_trading_ui.py`
- Use the streamlit-specific requirements: `requirements_streamlit.txt`
- Streamlit configuration is in `.streamlit/config.toml`

### 2. Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repository
3. Set the main file to: `enhanced_trading_ui.py`
4. Set requirements file to: `requirements_streamlit.txt`
5. Deploy!

### 3. Configuration Details

#### requirements_streamlit.txt
Contains minimal dependencies for cloud deployment:
- streamlit
- pandas
- numpy  
- plotly
- requests
- python-dotenv

#### .streamlit/config.toml
Streamlit cloud configuration:
- Headless mode enabled
- CORS settings configured
- Theme set to dark mode

### 4. Graceful Degradation
The dashboard includes fallback handling:
- **If plotly is missing**: Falls back to basic Streamlit charts
- **If API is unreachable**: Shows demo data
- **If dependencies fail**: Provides informative error messages

### 5. Local Development
To run locally:
```bash
pip install -r requirements_streamlit.txt
streamlit run enhanced_trading_ui.py
```

### 6. Troubleshooting
- **ModuleNotFoundError**: Use `requirements_streamlit.txt` instead of `requirements.txt`
- **Charts not showing**: Plotly fallback will show basic charts automatically
- **API connection issues**: Dashboard works in demo mode without backend connection

### 7. Features Available
- 📱 Mobile-responsive design
- 📊 Portfolio overview and metrics
- 🎯 Trading signals display
- ⚙️ Settings and controls
- 📈 Performance charts (with fallbacks)
- 🤖 AI insights and predictions
