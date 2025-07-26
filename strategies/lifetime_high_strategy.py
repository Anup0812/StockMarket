import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class LifetimeHighStrategy(BaseStrategy):
    """Lifetime High Strategy for best-in-class companies"""
    
    def __init__(self):
        super().__init__()
        self.applicable_groups = ['V40', 'V40_Next']
        self.max_discount_from_high = 0.30  # 30% below lifetime high
        self.target_gain_range = (0.30, 0.40)  # 30-40% gain target
    
    def get_signal(self, stock_data):
        """Get trading signal based on Lifetime High strategy"""
        if len(stock_data) < 100:
            return 'Neutral'
        
        # Check if conditions are met
        conditions = self._check_strategy_conditions(stock_data)
        
        if not conditions['qualified']:
            return 'Neutral'
        
        current_price = stock_data['Close'].iloc[-1]
        lifetime_high = conditions['lifetime_high']
        discount_from_high = conditions['discount_from_high']
        
        # Buy signal if below 30% from lifetime high and has good TTM numbers
        if (discount_from_high >= 0.20 and  # At least 20% discount
            conditions['ttm_numbers_good']):
            return 'Buy'
        
        # Sell signal if near or at lifetime high
        if current_price >= lifetime_high * 0.95:  # Within 5% of lifetime high
            return 'Sell'
        
        # Watch if conditions are developing
        if discount_from_high >= 0.15 and conditions['ttm_numbers_good']:
            return 'Watch'
        
        return 'Neutral'
    
    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed Lifetime High strategy analysis"""
        if len(stock_data) < 100:
            return None
        
        conditions = self._check_strategy_conditions(stock_data, fundamental_data)
        current_price = stock_data['Close'].iloc[-1]
        signal = self.get_signal(stock_data)
        
        entry_price = current_price
        target_price = conditions['lifetime_high']  # Target is always lifetime high
        
        # Calculate confidence
        confidence = self._calculate_confidence(stock_data, conditions, fundamental_data)
        
        signal_details = self.format_signal_details(signal, entry_price, target_price, confidence=confidence)
        
        # Add reason and additional details
        if signal == 'Buy':
            signal_details['reason'] = f"Strong fundamentals with {conditions['discount_from_high']*100:.1f}% discount from lifetime high"
        elif signal == 'Sell':
            signal_details['reason'] = "Price near lifetime high target"
        elif signal == 'Watch':
            signal_details['reason'] = "Good fundamentals, monitoring for better entry price"
        else:
            reason_parts = []
            if not conditions['ttm_numbers_good']:
                reason_parts.append("TTM numbers not at lifetime high")
            if conditions['discount_from_high'] < 0.20:
                reason_parts.append("Insufficient discount from lifetime high")
            signal_details['reason'] = "; ".join(reason_parts) if reason_parts else "Conditions not met"
        
        signal_details['lifetime_high'] = conditions['lifetime_high']
        signal_details['discount_from_high'] = f"{conditions['discount_from_high']*100:.1f}%"
        signal_details['ttm_revenue_growth'] = conditions.get('ttm_revenue_growth', 'N/A')
        signal_details['ttm_profit_growth'] = conditions.get('ttm_profit_growth', 'N/A')
        
        return {
            'strategy_name': 'Lifetime High Strategy',
            'signal_details': signal_details,
            'steps': self._get_strategy_steps(),
            'conditions': conditions,
            'averaging_allowed': signal != 'Buy' or not conditions.get('ttm_at_highest', False)
        }
    
    def get_chart_config(self, stock_data):
        """Get chart configuration with Lifetime High overlays"""
        if len(stock_data) < 100:
            return {}
        
        conditions = self._check_strategy_conditions(stock_data)
        lifetime_high = conditions['lifetime_high']
        
        overlays = []
        annotations = []
        
        # Draw lifetime high line
        overlays.append({
            'type': 'horizontal_line',
            'y': lifetime_high,
            'color': 'gold',
            'width': 3,
            'dash': 'solid'
        })
        
        # Draw 30% discount line
        discount_30_price = lifetime_high * 0.7
        overlays.append({
            'type': 'horizontal_line',
            'y': discount_30_price,
            'color': 'green',
            'width': 2,
            'dash': 'dash'
        })
        
        # Draw 20% discount line
        discount_20_price = lifetime_high * 0.8
        overlays.append({
            'type': 'horizontal_line',
            'y': discount_20_price,
            'color': 'orange',
            'width': 2,
            'dash': 'dot'
        })
        
        # Add annotations
        annotations.extend([
            {
                'type': 'annotation',
                'x': stock_data.index[-1].strftime('%Y-%m-%d'),
                'y': lifetime_high,
                'text': 'Lifetime High',
                'color': 'gold',
                'size': 12
            },
            {
                'type': 'annotation',
                'x': stock_data.index[-1].strftime('%Y-%m-%d'),
                'y': discount_30_price,
                'text': '30% Discount',
                'color': 'green',
                'size': 10
            },
            {
                'type': 'annotation',
                'x': stock_data.index[-1].strftime('%Y-%m-%d'),
                'y': discount_20_price,
                'text': '20% Discount',
                'color': 'orange',
                'size': 10
            }
        ])
        
        # Mark current position
        current_price = stock_data['Close'].iloc[-1]
        annotations.append({
            'type': 'annotation',
            'x': stock_data.index[-1].strftime('%Y-%m-%d'),
            'y': current_price,
            'text': 'Current',
            'color': 'blue',
            'size': 10
        })
        
        return {
            'overlays': overlays,
            'annotations': annotations
        }
    
    def _check_strategy_conditions(self, stock_data, fundamental_data=None):
        """Check if all strategy conditions are met"""
        conditions = {
            'qualified': False,
            'lifetime_high': 0,
            'discount_from_high': 0,
            'ttm_numbers_good': False,
            'ttm_at_highest': False
        }
        
        # Calculate lifetime high
        lifetime_high = stock_data['High'].max()
        current_price = stock_data['Close'].iloc[-1]
        discount_from_high = (lifetime_high - current_price) / lifetime_high
        
        conditions['lifetime_high'] = lifetime_high
        conditions['discount_from_high'] = discount_from_high
        
        # Check TTM numbers if fundamental data is available
        if fundamental_data:
            ttm_analysis = self._analyze_ttm_numbers(fundamental_data)
            conditions.update(ttm_analysis)
        else:
            # Simplified check based on recent price performance and volume
            conditions['ttm_numbers_good'] = self._estimate_fundamental_strength(stock_data)
        
        # Overall qualification
        conditions['qualified'] = (
            discount_from_high <= self.max_discount_from_high and
            conditions['ttm_numbers_good']
        )
        
        return conditions
    
    def _analyze_ttm_numbers(self, fundamental_data):
        """Analyze TTM (Trailing Twelve Months) numbers"""
        ttm_analysis = {
            'ttm_numbers_good': False,
            'ttm_at_highest': False,
            'ttm_revenue_growth': 0,
            'ttm_profit_growth': 0
        }
        
        try:
            # Get growth metrics
            revenue_growth = fundamental_data.get('revenue_growth', 0)
            earnings_growth = fundamental_data.get('earnings_growth', 0)
            profit_margins = fundamental_data.get('profit_margins', 0)
            
            # Check if TTM numbers are strong
            if (revenue_growth > 0.10 and  # 10% revenue growth
                earnings_growth > 0.15 and  # 15% earnings growth
                profit_margins > 0.15):  # 15% profit margins
                
                ttm_analysis['ttm_numbers_good'] = True
                ttm_analysis['ttm_revenue_growth'] = f"{revenue_growth*100:.1f}%"
                ttm_analysis['ttm_profit_growth'] = f"{earnings_growth*100:.1f}%"
                
                # Check if these are lifetime highs for the metrics
                # This would require historical data comparison
                # For now, assume strong current numbers indicate good position
                if revenue_growth > 0.20 and earnings_growth > 0.25:
                    ttm_analysis['ttm_at_highest'] = True
            
        except Exception as e:
            print(f"Error analyzing TTM numbers: {e}")
        
        return ttm_analysis
    
    def _estimate_fundamental_strength(self, stock_data):
        """Estimate fundamental strength from price and volume data"""
        # This is a simplified approach when fundamental data is not available
        
        # Check recent volume trends (indicating institutional interest)
        recent_volume = stock_data['Volume'].tail(30).mean()
        historical_volume = stock_data['Volume'].mean()
        volume_strength = recent_volume > historical_volume * 1.2
        
        # Check price stability during market volatility
        recent_volatility = stock_data['Close'].tail(30).std() / stock_data['Close'].tail(30).mean()
        historical_volatility = stock_data['Close'].std() / stock_data['Close'].mean()
        stability_strength = recent_volatility <= historical_volatility
        
        # Check for consistent upward bias in recent months
        monthly_returns = stock_data['Close'].resample('ME').last().pct_change().tail(6)
        positive_months = (monthly_returns > 0).sum()
        return_consistency = positive_months >= 4  # At least 4 out of 6 months positive
        
        # Overall strength estimation
        strength_indicators = [volume_strength, stability_strength, return_consistency]
        return sum(strength_indicators) >= 2  # At least 2 out of 3 indicators positive
    
    def _calculate_confidence(self, stock_data, conditions, fundamental_data):
        """Calculate confidence score for Lifetime High strategy"""
        confidence = 40  # Base confidence
        
        # Discount level (better discounts = higher confidence)
        discount = conditions['discount_from_high']
        if discount >= 0.25:
            confidence += 25
        elif discount >= 0.20:
            confidence += 20
        elif discount >= 0.15:
            confidence += 15
        
        # TTM numbers quality
        if conditions['ttm_numbers_good']:
            confidence += 20
            if conditions.get('ttm_at_highest', False):
                confidence += 10
        
        # Fundamental strength indicators
        if fundamental_data:
            pe_ratio = fundamental_data.get('pe_ratio', 0)
            debt_to_equity = fundamental_data.get('debt_to_equity', 0)
            roe = fundamental_data.get('return_on_equity', 0)
            
            # Low valuation with strong fundamentals
            if pe_ratio > 0 and pe_ratio < 20:  # Reasonable P/E
                confidence += 5
            if debt_to_equity < 0.5:  # Low debt
                confidence += 5
            if roe > 0.15:  # Good ROE
                confidence += 5
        
        # Market conditions and sector performance
        # This could be enhanced with sector comparison
        confidence += 5  # Basic market condition assumption
        
        return min(100, confidence)
    
    def _get_strategy_steps(self):
        """Get strategy implementation steps"""
        return [
            "1. Identify companies posting lifetime high TTM revenue and profits",
            "2. Verify company is from V40 or V40 Next group (best-in-class)",
            "3. Check if stock price is below 30% from lifetime high",
            "4. Confirm strong fundamental metrics (growth, margins, ROE)",
            "5. Enter buy signal when price is 20-30% below lifetime high",
            "6. Allow averaging on further declines if TTM numbers are not at highest",
            "7. Do NOT average if TTM numbers are at their highest levels",
            "8. Target is always the lifetime high price",
            "9. Aim for 30-40% gain in single trade for best companies"
        ]
