import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class V10Strategy(BaseStrategy):
    """V10 Strategy - Add-on to RHS and CWH strategies"""
    
    def __init__(self):
        super().__init__()
        self.applicable_groups = ['V40', 'V40_Next']
        self.fall_threshold = 0.10  # 10% fall threshold
        self.min_gap_between_trades = 0.05  # 5% minimum gap between V10 trades
    
    def get_signal(self, stock_data):
        """Get trading signal based on V10 conditions"""
        # V10 is an add-on strategy, so it needs to be used with RHS or CWH
        # This method should be called after checking RHS/CWH qualification
        
        if len(stock_data) < 50:
            return 'Neutral'
        
        # Check if there's been a 10% fall from a recent high
        v10_opportunities = self._find_v10_opportunities(stock_data)
        
        if not v10_opportunities:
            return 'Neutral'
        
        current_price = stock_data['Close'].iloc[-1]
        
        for opportunity in v10_opportunities:
            # Check if we're near the reversal point
            if current_price <= opportunity['buy_level'] * 1.02:  # Within 2% of buy level
                return 'Buy'
            
            # Check if we've reached the reversal target
            if current_price >= opportunity['target_price'] * 0.98:
                return 'Sell'
        
        return 'Watch'  # Monitoring for potential V10 opportunities
    
    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed V10 analysis"""
        if len(stock_data) < 50:
            return None
        
        v10_opportunities = self._find_v10_opportunities(stock_data)
        current_price = stock_data['Close'].iloc[-1]
        signal = self.get_signal(stock_data)
        
        if not v10_opportunities:
            return {
                'strategy_name': 'V10 Strategy',
                'signal_details': self.format_signal_details('Neutral', current_price, None),
                'steps': self._get_strategy_steps(),
                'opportunities': [],
                'note': 'V10 is an add-on strategy. Stock must first qualify under RHS or CWH.'
            }
        
        active_opportunity = v10_opportunities[0]
        
        entry_price = active_opportunity['buy_level']
        target_price = active_opportunity['target_price']
        
        # Calculate confidence
        confidence = self._calculate_confidence(stock_data, active_opportunity)
        
        signal_details = self.format_signal_details(signal, entry_price, target_price, confidence=confidence)
        
        # Add reason and additional details
        if signal == 'Buy':
            signal_details['reason'] = f"10% fall from ₹{active_opportunity['high_price']:.2f} to ₹{active_opportunity['low_price']:.2f}"
        elif signal == 'Sell':
            signal_details['reason'] = "Reversal target reached"
        else:
            signal_details['reason'] = "Monitoring for 10% fall reversal opportunity"
        
        signal_details['fall_percentage'] = active_opportunity['fall_percentage']
        signal_details['high_price'] = active_opportunity['high_price']
        signal_details['low_price'] = active_opportunity['low_price']
        
        return {
            'strategy_name': 'V10 Strategy',
            'signal_details': signal_details,
            'steps': self._get_strategy_steps(),
            'opportunities': v10_opportunities,
            'active_opportunity': active_opportunity,
            'note': 'This strategy is applicable only after RHS or CWH qualification.'
        }
    
    def get_chart_config(self, stock_data):
        """Get chart configuration with V10 overlays"""
        if len(stock_data) < 50:
            return {}
        
        v10_opportunities = self._find_v10_opportunities(stock_data)
        
        overlays = []
        annotations = []
        
        for i, opportunity in enumerate(v10_opportunities):
            # Draw fall line
            overlays.append({
                'type': 'line',
                'x0': opportunity['high_date'].strftime('%Y-%m-%d'),
                'x1': opportunity['low_date'].strftime('%Y-%m-%d'),
                'y0': opportunity['high_price'],
                'y1': opportunity['low_price'],
                'color': 'red',
                'width': 3
            })
            
            # Draw target line
            overlays.append({
                'type': 'horizontal_line',
                'y': opportunity['target_price'],
                'color': 'green',
                'width': 2,
                'dash': 'dot'
            })
            
            # Add annotations
            annotations.extend([
                {
                    'type': 'annotation',
                    'x': opportunity['high_date'].strftime('%Y-%m-%d'),
                    'y': opportunity['high_price'],
                    'text': f'V10 High {i+1}',
                    'color': 'red',
                    'size': 10
                },
                {
                    'type': 'annotation',
                    'x': opportunity['low_date'].strftime('%Y-%m-%d'),
                    'y': opportunity['low_price'],
                    'text': f'10% Fall',
                    'color': 'red',
                    'size': 10
                },
                {
                    'type': 'annotation',
                    'x': opportunity['low_date'].strftime('%Y-%m-%d'),
                    'y': opportunity['target_price'],
                    'text': f'V10 Target',
                    'color': 'green',
                    'size': 10
                }
            ])
        
        return {
            'overlays': overlays,
            'annotations': annotations
        }
    
    def _find_v10_opportunities(self, stock_data):
        """Find V10 opportunities (10% falls and their reversals)"""
        opportunities = []
        
        # Find significant highs first
        highs = self._find_significant_highs(stock_data)
        
        for high_point in highs:
            # Look for data after this high
            after_high = stock_data.loc[high_point['date']:]
            
            if len(after_high) < 10:
                continue
            
            # Find the lowest point after the high
            low_idx = after_high['Low'].idxmin()
            low_price = after_high.loc[low_idx, 'Low']
            
            # Calculate fall percentage
            fall_percentage = (high_point['price'] - low_price) / high_point['price']
            
            # Check if fall is at least 10%
            if fall_percentage >= self.fall_threshold:
                
                # Calculate reversal target (back to the high or the fall amount)
                target_price = low_price + (high_point['price'] - low_price)
                
                # Buy level is at or near the low
                buy_level = low_price * 1.02  # 2% above the low for practical entry
                
                opportunity = {
                    'high_date': high_point['date'],
                    'high_price': high_point['price'],
                    'low_date': low_idx,
                    'low_price': low_price,
                    'fall_percentage': fall_percentage * 100,
                    'buy_level': buy_level,
                    'target_price': target_price,
                    'opportunity_age_days': (stock_data.index[-1] - low_idx).days
                }
                
                # Check if this opportunity is still valid (not too old)
                if opportunity['opportunity_age_days'] <= 90:  # Within 3 months
                    opportunities.append(opportunity)
        
        # Sort by recency and fall magnitude
        opportunities.sort(key=lambda x: (x['opportunity_age_days'], -x['fall_percentage']))
        
        # Filter out opportunities that are too close to each other
        filtered_opportunities = []
        for opp in opportunities:
            is_valid = True
            for existing in filtered_opportunities:
                price_diff = abs(opp['buy_level'] - existing['buy_level']) / existing['buy_level']
                if price_diff < self.min_gap_between_trades:
                    is_valid = False
                    break
            
            if is_valid:
                filtered_opportunities.append(opp)
        
        return filtered_opportunities[:3]  # Return top 3 opportunities
    
    def _find_significant_highs(self, stock_data, window=5):
        """Find significant high points for V10 analysis"""
        highs = []
        
        for i in range(window, len(stock_data) - window):
            current_high = stock_data['High'].iloc[i]
            
            # Check if current point is higher than surrounding points
            is_significant = True
            for j in range(i - window, i + window + 1):
                if j != i and stock_data['High'].iloc[j] >= current_high:
                    is_significant = False
                    break
            
            if is_significant:
                highs.append({
                    'date': stock_data.index[i],
                    'price': current_high,
                    'index': i
                })
        
        # Filter to only recent highs (within reasonable time frame)
        recent_date = stock_data.index[-1] - pd.Timedelta(days=180)  # 6 months
        recent_highs = [h for h in highs if h['date'] >= recent_date]
        
        return recent_highs
    
    def _calculate_confidence(self, stock_data, opportunity):
        """Calculate confidence score for V10 opportunity"""
        confidence = 60  # Base confidence for V10
        
        # Fall magnitude (larger falls are more significant)
        if opportunity['fall_percentage'] > 15:
            confidence += 20
        elif opportunity['fall_percentage'] > 12:
            confidence += 15
        elif opportunity['fall_percentage'] > 10:
            confidence += 10
        
        # Recency (more recent opportunities are better)
        if opportunity['opportunity_age_days'] <= 30:
            confidence += 15
        elif opportunity['opportunity_age_days'] <= 60:
            confidence += 10
        elif opportunity['opportunity_age_days'] <= 90:
            confidence += 5
        
        # Volume during the fall
        fall_period = stock_data.loc[opportunity['high_date']:opportunity['low_date']]
        if len(fall_period) > 0:
            fall_volume = fall_period['Volume'].mean()
            overall_volume = stock_data['Volume'].mean()
            if fall_volume > overall_volume:
                confidence += 5
        
        return min(100, confidence)
    
    def _get_strategy_steps(self):
        """Get strategy implementation steps"""
        return [
            "1. Stock must first qualify under RHS or CWH strategy",
            "2. Monitor for 10% fall from any high after initial buy signal",
            "3. Enter V10 trade when reversal of the fall begins",
            "4. Target is the reversal of the entire fall amount",
            "5. Subsequent V10 trades must be at least 5% lower than previous",
            "6. No stop-loss is used in this strategy",
            "7. This is an add-on strategy to enhance RHS/CWH returns",
            "8. Apply only to V40 and V40 Next companies"
        ]
    
    def check_rhs_cwh_qualification(self, stock_data, rhs_strategy, cwh_strategy):
        """Check if stock qualifies under RHS or CWH before applying V10"""
        rhs_signal = rhs_strategy.get_signal(stock_data)
        cwh_signal = cwh_strategy.get_signal(stock_data)
        
        return rhs_signal in ['Buy', 'Watch'] or cwh_signal in ['Buy', 'Watch']
