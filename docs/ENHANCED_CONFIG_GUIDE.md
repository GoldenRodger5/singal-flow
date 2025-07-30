# Enhanced Signal Flow Configuration Guide

## New Enhanced Features

### 1. Market Regime Detection
- `REGIME_DETECTION_ENABLED=true` - Enable adaptive strategy based on market conditions
- `VOLATILITY_LOOKBACK_DAYS=20` - Days to analyze for volatility regime
- `TREND_DETECTION_PERIOD=50` - Period for trend strength calculation

### 2. Enhanced Technical Indicators
- `RSI_ZSCORE_ENABLED=true` - Use volatility-adjusted RSI instead of static thresholds
- `ORDER_FLOW_ANALYSIS_ENABLED=true` - Analyze buying vs selling pressure
- `SECTOR_RELATIVE_STRENGTH_ENABLED=true` - Compare performance to sector/market

### 3. Advanced Position Sizing
- `KELLY_CRITERION_SIZING=true` - Optimal position sizing based on win rate and odds
- `VOLATILITY_SCALING_ENABLED=true` - Adjust position size based on volatility
- `CORRELATION_ADJUSTMENT_ENABLED=true` - Reduce size for correlated positions

### 4. Dynamic Risk Management
- `MAX_PORTFOLIO_VOLATILITY=0.15` - Target 15% annual portfolio volatility
- `MAX_SECTOR_EXPOSURE_PERCENT=0.30` - Maximum 30% exposure to any sector
- `MAX_PORTFOLIO_RISK_PERCENT=0.02` - Maximum 2% portfolio risk per trade

## How Enhanced Features Work

### Regime Detection
The system now automatically detects market regimes:
- **Trending High Vol**: Momentum strategies, wider stops
- **Trending Low Vol**: Trend following, tighter stops  
- **Mean Reverting High Vol**: Contrarian plays, quick exits
- **Mean Reverting Low Vol**: Range trading strategies
- **Uncertain**: Conservative approach, reduced position sizes

### Enhanced Indicators
Instead of traditional RSI(30/70) and MACD, the system uses:
- **RSI Z-Score**: Volatility-adjusted RSI that adapts to market conditions
- **Momentum Divergence**: Looks for price/momentum disconnects
- **Volume Price Trend**: Alternative to VWAP less susceptible to manipulation
- **Order Flow Imbalance**: Estimates institutional buying/selling pressure
- **Adaptive Bollinger Bands**: Bands that adjust to volatility regime

### Smart Position Sizing
Position sizes now consider:
- Signal confidence and strength
- Current market volatility
- Correlation with existing positions
- Kelly Criterion optimization
- Maximum risk and exposure limits

## Migration from Old System

### Automatic Fallbacks
- If enhanced components fail, system falls back to traditional indicators
- All existing functionality remains intact
- Enhanced features are additive, not replacement

### Gradual Adoption
1. Install enhanced dependencies: `python install_enhanced_deps.py`
2. Update configuration with enhanced parameters
3. System will automatically detect and use enhanced features
4. Monitor performance improvements through learning dashboard

## Performance Expectations

### Expected Improvements
- **Sharpe Ratio**: 15-25% improvement through better signal quality
- **Drawdowns**: Reduced through regime-aware risk management
- **Win Rate**: Improved through better entry timing
- **Position Sizing**: Optimal sizing increases long-term returns

### Risk Considerations
- Enhanced system requires more data and computation
- Learning period needed for optimal performance (30+ trades)
- Market regime changes may temporarily reduce performance
- Monitor system closely during first month of enhanced operation

## Troubleshooting

### Common Issues
1. **Import Errors**: Run `python install_enhanced_deps.py`
2. **Slow Performance**: Enable `USE_NUMBA_ACCELERATION=true`
3. **Memory Usage**: Reduce `VOLATILITY_LOOKBACK_DAYS` if needed
4. **False Signals**: Increase `MIN_SAMPLES_FOR_LEARNING` for stability

### Monitoring
- Check regime detection accuracy in dashboard
- Monitor position sizing recommendations
- Track performance vs baseline traditional system
- Review adaptive threshold adjustments

## Support
For issues with enhanced features, check logs for:
- "Enhanced components not available" warnings
- Regime detection errors
- Position sizing calculation errors
- Indicator calculation failures
