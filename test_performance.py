#!/usr/bin/env python3
"""
Performance Testing Suite for Enhanced Features
Tests speed improvements and feature availability without requiring market data.
"""
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

def generate_synthetic_market_data(days: int = 252, ticker: str = "TEST") -> pd.DataFrame:
    """Generate realistic synthetic market data for testing."""
    np.random.seed(42)  # Consistent results
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), end=datetime.now(), freq='D')
    
    # Generate realistic price movements
    initial_price = 100.0
    daily_returns = np.random.normal(0.0008, 0.02, len(dates))  # ~20% annual vol
    prices = initial_price * np.exp(np.cumsum(daily_returns))
    
    # Generate volume with occasional spikes
    base_volume = 1000000
    volume_variation = np.random.lognormal(0, 0.3, len(dates))
    volume = (base_volume * volume_variation).astype(int)
    
    # Generate OHLC from close prices
    high = prices * (1 + np.random.uniform(0, 0.03, len(dates)))
    low = prices * (1 - np.random.uniform(0, 0.03, len(dates)))
    open_prices = np.roll(prices, 1)  # Previous close as open
    open_prices[0] = prices[0]
    
    return pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': prices,
        'volume': volume
    }, index=dates)

def test_numba_performance():
    """Test Numba acceleration performance."""
    print("🚀 Testing Numba Acceleration Performance")
    print("-" * 50)
    
    # Test different data sizes
    data_sizes = [100, 500, 1000, 2500]
    results = {}
    
    for size in data_sizes:
        data = generate_synthetic_market_data(size)
        prices = data['close'].values
        
        print(f"\n📊 Testing with {size} data points...")
        
        # Test RSI calculation speed
        try:
            from services.numba_accelerated import fast_rsi_calculation, NUMBA_AVAILABLE
            
            if NUMBA_AVAILABLE:
                # Numba version
                start_time = time.time()
                numba_rsi = fast_rsi_calculation(prices, 14)
                numba_time = time.time() - start_time
                
                # Pandas version
                start_time = time.time()
                import pandas_ta as ta
                pandas_rsi = ta.rsi(data['close'], length=14).values
                pandas_time = time.time() - start_time
                
                speedup = pandas_time / numba_time if numba_time > 0 else 0
                
                print(f"   📈 RSI Calculation:")
                print(f"      Pandas: {pandas_time*1000:.2f}ms")
                print(f"      Numba:  {numba_time*1000:.2f}ms")
                print(f"      Speedup: {speedup:.1f}x faster")
                
                results[size] = {
                    'pandas_time': pandas_time,
                    'numba_time': numba_time,
                    'speedup': speedup
                }
            else:
                print("   ⚠️  Numba not available - install with: pip install numba")
                results[size] = {'error': 'numba_not_available'}
                
        except Exception as e:
            print(f"   ❌ Error testing performance: {e}")
            results[size] = {'error': str(e)}
    
    # Summary
    if results and not all('error' in r for r in results.values()):
        avg_speedup = np.mean([r['speedup'] for r in results.values() if 'speedup' in r])
        print(f"\n✅ Average Performance Improvement: {avg_speedup:.1f}x faster")
        
        if avg_speedup > 2:
            print("🎉 Excellent performance boost achieved!")
        elif avg_speedup > 1.5:
            print("👍 Good performance improvement!")
        else:
            print("📈 Modest performance improvement")
    
    return results

def test_enhanced_indicators():
    """Test enhanced indicator functionality."""
    print("\n🧠 Testing Enhanced Indicators")
    print("-" * 50)
    
    data = generate_synthetic_market_data(100)
    test_results = {}
    
    # Test RSI Z-Score
    try:
        from services.enhanced_indicators import EnhancedIndicators
        from services.config import Config
        
        config = Config()
        indicators = EnhancedIndicators(config)
        
        start_time = time.time()
        rsi_zscore_result = indicators.calculate_rsi_zscore(data)
        calculation_time = time.time() - start_time
        
        print(f"✅ RSI Z-Score: {rsi_zscore_result.signal} (strength: {rsi_zscore_result.strength:.2f})")
        print(f"   Value: {rsi_zscore_result.value:.3f}")
        print(f"   Confidence: {rsi_zscore_result.confidence:.2f}")
        print(f"   Calculation time: {calculation_time*1000:.1f}ms")
        
        if 'calculation_method' in rsi_zscore_result.additional_data:
            method = rsi_zscore_result.additional_data['calculation_method']
            boost = rsi_zscore_result.additional_data.get('performance_boost', 'N/A')
            print(f"   Method: {method} ({boost})")
        
        test_results['rsi_zscore'] = 'PASS'
        
    except Exception as e:
        print(f"❌ RSI Z-Score test failed: {e}")
        test_results['rsi_zscore'] = 'FAIL'
    
    # Test Order Flow Analysis
    try:
        order_flow_result = indicators.calculate_order_flow_imbalance(data)
        
        print(f"✅ Order Flow Analysis: {order_flow_result.signal} (strength: {order_flow_result.strength:.2f})")
        print(f"   Flow value: {order_flow_result.value:.3f}")
        print(f"   Confidence: {order_flow_result.confidence:.2f}")
        
        if 'signal_components' in order_flow_result.additional_data:
            components = order_flow_result.additional_data['signal_components']
            print(f"   Components: {', '.join(components[:3])}...")  # Show first 3
        
        test_results['order_flow'] = 'PASS'
        
    except Exception as e:
        print(f"❌ Order Flow test failed: {e}")
        test_results['order_flow'] = 'FAIL'
    
    # Test Sector Relative Strength
    try:
        sector_rs_result = indicators.calculate_sector_relative_strength('AAPL', data)
        
        print(f"✅ Sector Relative Strength: {sector_rs_result.signal} (strength: {sector_rs_result.strength:.2f})")
        print(f"   Relative performance: {sector_rs_result.value:.1%}")
        print(f"   Confidence: {sector_rs_result.confidence:.2f}")
        
        if 'sector_etf' in sector_rs_result.additional_data:
            sector = sector_rs_result.additional_data['sector_etf']
            print(f"   Sector ETF: {sector}")
        
        test_results['sector_relative_strength'] = 'PASS'
        
    except Exception as e:
        print(f"❌ Sector Relative Strength test failed: {e}")
        test_results['sector_relative_strength'] = 'FAIL'
    
    return test_results

def test_market_regime_detection():
    """Test market regime detection."""
    print("\n🌊 Testing Market Regime Detection")
    print("-" * 50)
    
    # Generate different market conditions
    test_scenarios = {
        'trending_bull': {'drift': 0.05, 'volatility': 0.15},
        'trending_bear': {'drift': -0.03, 'volatility': 0.20},
        'sideways_low_vol': {'drift': 0.001, 'volatility': 0.10},
        'sideways_high_vol': {'drift': 0.001, 'volatility': 0.30},
    }
    
    try:
        from services.market_regime_detector import MarketRegimeDetector
        from services.config import Config
        
        config = Config()
        detector = MarketRegimeDetector(config)
        
        for scenario_name, params in test_scenarios.items():
            # Generate scenario-specific data
            np.random.seed(hash(scenario_name) % 1000)
            days = 100
            dates = pd.date_range(start=datetime.now() - timedelta(days=days-1), end=datetime.now(), freq='D')
            
            returns = np.random.normal(params['drift']/252, params['volatility']/np.sqrt(252), days)
            prices = 100 * np.exp(np.cumsum(returns))
            
            data = pd.DataFrame({
                'open': np.roll(prices, 1),  # Previous close as open
                'close': prices,
                'high': prices * 1.02,
                'low': prices * 0.98,
                'volume': np.random.randint(100000, 1000000, days)
            }, index=dates)
            
            regime_data = detector.detect_market_regime(data)
            
            print(f"📈 {scenario_name.replace('_', ' ').title()}:")
            print(f"   Detected regime: {regime_data.regime.value}")
            print(f"   Confidence: {regime_data.confidence:.2f}")
            print(f"   Volatility percentile: {regime_data.volatility_percentile:.1f}")
            print(f"   Trend strength: {regime_data.trend_strength:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Market regime detection test failed: {e}")
        return False

def test_position_sizing():
    """Test Kelly Criterion position sizing."""
    print("\n💰 Testing Kelly Criterion Position Sizing")
    print("-" * 50)
    
    try:
        from services.enhanced_position_sizer import EnhancedPositionSizer
        from services.config import Config
        
        config = Config()
        sizer = EnhancedPositionSizer(config)
        
        # Test scenarios
        test_trades = [
            {'symbol': 'AAPL', 'entry': 150, 'stop': 145, 'confidence': 7.5, 'description': 'Conservative tech trade'},
            {'symbol': 'TSLA', 'entry': 200, 'stop': 190, 'confidence': 8.5, 'description': 'High confidence growth'},
            {'symbol': 'SPY', 'entry': 400, 'stop': 395, 'confidence': 6.0, 'description': 'Low confidence market'},
        ]
        
        portfolio_value = 100000
        
        for trade in test_trades:
            result = sizer.calculate_position_size(
                symbol=trade['symbol'],
                entry_price=trade['entry'],
                stop_loss=trade['stop'],
                confidence=trade['confidence'],
                technical_signals={'composite_strength': trade['confidence']/10},
                portfolio_value=portfolio_value
            )
            
            risk_amount = abs(trade['entry'] - trade['stop']) * (result.position_size / trade['entry'])
            risk_pct = (risk_amount / portfolio_value) * 100
            
            print(f"📊 {trade['description']}:")
            print(f"   Symbol: {trade['symbol']} @ ${trade['entry']}")
            print(f"   Position size: ${result.position_size:,.0f} ({result.position_percentage:.1%})")
            print(f"   Kelly fraction: {result.kelly_fraction:.3f}")
            print(f"   Risk amount: ${risk_amount:,.0f} ({risk_pct:.1f}%)")
            print(f"   Volatility adjustment: {result.volatility_adjustment:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Position sizing test failed: {e}")
        return False

def test_system_integration():
    """Test full system integration."""
    print("\n🔗 Testing System Integration")
    print("-" * 50)
    
    try:
        # Test config loading
        from services.config import Config
        config = Config()
        
        enhanced_features = [
            'REGIME_DETECTION_ENABLED',
            'VOLATILITY_SCALING_ENABLED', 
            'KELLY_CRITERION_SIZING',
            'RSI_ZSCORE_ENABLED',
            'ORDER_FLOW_ANALYSIS_ENABLED',
            'SECTOR_RELATIVE_STRENGTH_ENABLED',
            'CORRELATION_ADJUSTMENT_ENABLED'
        ]
        
        enabled_features = []
        for feature in enhanced_features:
            if hasattr(config, feature) and getattr(config, feature):
                enabled_features.append(feature)
        
        print(f"✅ Enhanced features enabled: {len(enabled_features)}/{len(enhanced_features)}")
        for feature in enabled_features:
            print(f"   ✓ {feature}")
        
        # Test main trading pipeline integration
        from services.indicators import TechnicalIndicators
        
        data = generate_synthetic_market_data(50)
        tech_indicators = TechnicalIndicators(config)
        
        signals = tech_indicators.get_enhanced_signals('TEST', data)
        
        print(f"✅ Technical indicators integration: {len(signals)} signals generated")
        
        if 'market_regime' in signals:
            regime_info = signals['market_regime']
            print(f"   Market regime: {regime_info['regime']} (confidence: {regime_info['confidence']:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ System integration test failed: {e}")
        return False

def main():
    """Run all performance tests."""
    print("🎯 Enhanced Trading System - Performance Testing Suite")
    print("=" * 70)
    print("Testing enhanced features without requiring live market data...")
    print()
    
    start_time = time.time()
    
    # Run all tests
    test_results = {}
    
    try:
        test_results['numba_performance'] = test_numba_performance()
    except Exception as e:
        print(f"❌ Numba performance test failed: {e}")
        test_results['numba_performance'] = False
    
    try:
        test_results['enhanced_indicators'] = test_enhanced_indicators()
    except Exception as e:
        print(f"❌ Enhanced indicators test failed: {e}")
        test_results['enhanced_indicators'] = False
    
    try:
        test_results['regime_detection'] = test_market_regime_detection()
    except Exception as e:
        print(f"❌ Regime detection test failed: {e}")
        test_results['regime_detection'] = False
    
    try:
        test_results['position_sizing'] = test_position_sizing()
    except Exception as e:
        print(f"❌ Position sizing test failed: {e}")
        test_results['position_sizing'] = False
    
    try:
        test_results['system_integration'] = test_system_integration()
    except Exception as e:
        print(f"❌ System integration test failed: {e}")
        test_results['system_integration'] = False
    
    # Summary
    total_time = time.time() - start_time
    
    print("\n" + "="*70)
    print("📋 PERFORMANCE TEST SUMMARY")
    print("="*70)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    print(f"⏱️  Total test time: {total_time:.2f} seconds")
    print(f"✅ Tests passed: {passed_tests}/{total_tests}")
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name.replace('_', ' ').title()}")
    
    if passed_tests == total_tests:
        print("\n🎉 All performance tests passed!")
        print("🚀 Your enhanced trading system is operating at full capacity!")
    elif passed_tests >= total_tests * 0.75:
        print("\n👍 Most tests passed - system is largely functional!")
        print("💡 Some features may need attention.")
    else:
        print("\n⚠️  Several tests failed - check your installation.")
        print("💡 Run: python install_enhanced_features.py")
    
    print(f"\n📊 System Performance Rating: {(passed_tests/total_tests)*100:.0f}%")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
