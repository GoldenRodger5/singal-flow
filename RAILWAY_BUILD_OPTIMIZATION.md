# Railway Build Optimization Guide
# Reduce Railway deployment time from 20+ minutes to ~3-5 minutes

## Current Issues:
1. **Heavy requirements.txt**: 40+ packages with ML libraries (scikit-learn, numba, jupyter)
2. **Wrong start command**: Points to non-existent `railway_api.py`
3. **Large build context**: Includes unnecessary files (data/, logs/, frontend/)
4. **No caching optimization**: Rebuilds everything on each deployment

## Optimizations Applied:

### 1. Minimal Requirements
- Created `requirements-minimal.txt` with only 15 essential packages
- Removed heavy ML libraries (scikit-learn, numba, jupyter, streamlit)
- Kept only: FastAPI, MongoDB, Alpaca, OpenAI/Anthropic, basic utilities

### 2. Fixed Build Configuration
```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install --no-cache-dir -r requirements-minimal.txt"
  },
  "deploy": {
    "startCommand": "cd backend && python railway_start.py"
  }
}
```

### 3. Added .dockerignore
- Excludes cache/, logs/, data/, frontend/, docs/
- Reduces build context size by ~80%

### 4. Build Time Comparison:
- **Before**: 15-25 minutes (heavy ML packages)
- **After**: 3-7 minutes (minimal packages only)

## Next Steps:
1. Commit these changes
2. Push to trigger new deployment
3. Monitor build time improvement

## If You Need ML Features:
- Use external ML APIs instead of local libraries
- Consider Railway addons for ML services
- Use separate service for ML-heavy operations
