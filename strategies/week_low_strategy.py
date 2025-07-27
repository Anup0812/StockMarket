import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class WeekLowStrategy(BaseStrategy):
    """52 Week Low Strategy for value investing in quality companies"""

    def __init__(self):
        super().__init__()
        # Remove group restriction for testing - you can add it back later
        self.applicable_groups = ['V40', 'V40_Next']  # Apply to all groups for now
        self.low_threshold_days = 5  # Consider stock at 52-week low if within 5 trading days
        self.near_low_percentage = 0.05  # Within 5% of 52-week low
        self.target_multiplier = 1.0  # Target is lifetime high (no multiplier)

    def get_signal(self, stock_data):
        """Get trading signal based on 52 Week Low strategy"""
        if len(stock_data) < 240:  # Need at least 1 year of data
            return 'Neutral'

        # Check if conditions are met
        conditions = self._check_strategy_conditions(stock_data)

        if not conditions['qualified']:
            return 'Neutral'

        current_price = stock_data['Close'].iloc[-1]
        week_52_low = conditions['week_52_low']
        lifetime_high = conditions['lifetime_high']
        distance_from_low = conditions['distance_from_low']

        # Buy signal if at or very near 52-week low
        if distance_from_low <= self.near_low_percentage:
            return 'Buy'

        # Sell signal if near lifetime high (within 5%)
        if current_price >= lifetime_high * 0.95:
            return 'Sell'

        # Watch if approaching 52-week low (within 10%)
        if distance_from_low <= 0.10:
            return 'Watch'

        return 'Neutral'

    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed 52 Week Low strategy analysis"""
        if len(stock_data) < 240:
            # Return analysis even with insufficient data
            return {
                'strategy_name': '52 Week Low Strategy',
                'signal_details': {
                    'signal': 'Neutral',
                    'reason': f'Insufficient data (need at least 252 days, have {len(stock_data)})',
                    'entry_price': 0,
                    'target_price': 0,
                    'potential_gain': 0,
                    'confidence': 0,
                    'stop_loss': None
                },
                'steps': self._get_strategy_steps(),
                'conditions': {},
                'averaging_allowed': True
            }

        conditions = self._check_strategy_conditions(stock_data, fundamental_data)
        current_price = stock_data['Close'].iloc[-1]
        signal = self.get_signal(stock_data)

        entry_price = conditions['week_52_low']  # Entry at 52-week low
        target_price = conditions['lifetime_high']  # Target is lifetime high

        # Calculate stop loss (10% below 52-week low)
        stop_loss = entry_price * 0.90

        # Calculate confidence
        confidence = self._calculate_confidence(stock_data, conditions, fundamental_data)

        signal_details = self.format_signal_details(signal, entry_price, target_price, stop_loss, confidence)

        # Add reason and additional details
        if signal == 'Buy':
            signal_details[
                'reason'] = f"Stock at 52-week low ({conditions['distance_from_low'] * 100:.1f}% from low) with lifetime high target"
        elif signal == 'Sell':
            signal_details['reason'] = "Price near lifetime high target - time to book profits"
        elif signal == 'Watch':
            signal_details[
                'reason'] = f"Approaching 52-week low ({conditions['distance_from_low'] * 100:.1f}% from low) - prepare for entry"
        else:
            if not conditions['qualified']:
                signal_details['reason'] = f"Strategy conditions not met (upside potential: {((conditions['lifetime_high'] - conditions['week_52_low']) / conditions['week_52_low'] * 100):.1f}%)"
            else:
                signal_details[
                    'reason'] = f"Not near 52-week low (currently {conditions['distance_from_low'] * 100:.1f}% above low)"

        signal_details['week_52_low'] = conditions['week_52_low']
        signal_details['lifetime_high'] = conditions['lifetime_high']
        signal_details['distance_from_low'] = f"{conditions['distance_from_low'] * 100:.1f}%"
        signal_details[
            'potential_upside'] = f"{((conditions['lifetime_high'] - conditions['week_52_low']) / conditions['week_52_low'] * 100):.1f}%"
        signal_details[
            'current_vs_low'] = f"{((current_price - conditions['week_52_low']) / conditions['week_52_low'] * 100):.1f}%"

        return {
            'strategy_name': '52 Week Low Strategy',
            'signal_details': signal_details,
            'steps': self._get_strategy_steps(),
            'conditions': conditions,
            'averaging_allowed': True  # Always allow averaging for this strategy
        }

    def get_chart_config(self, stock_data):
        """Get chart configuration with 52 Week Low overlays"""
        if len(stock_data) < 240:
            return {}

        conditions = self._check_strategy_conditions(stock_data)
        week_52_low = conditions['week_52_low']
        lifetime_high = conditions['lifetime_high']
        current_price = stock_data['Close'].iloc[-1]

        overlays = []
        annotations = []

        # Draw lifetime high line (target)
        overlays.append({
            'type': 'horizontal_line',
            'y': lifetime_high,
            'color': 'gold',
            'width': 3,
            'dash': 'solid'
        })

        # Draw 52-week low line (entry point)
        overlays.append({
            'type': 'horizontal_line',
            'y': week_52_low,
            'color': 'red',
            'width': 3,
            'dash': 'solid'
        })

        # Draw 5% above 52-week low line (buy zone)
        buy_zone_price = week_52_low * 1.05
        overlays.append({
            'type': 'horizontal_line',
            'y': buy_zone_price,
            'color': 'green',
            'width': 2,
            'dash': 'dash'
        })

        # Draw 10% above 52-week low line (watch zone)
        watch_zone_price = week_52_low * 1.10
        overlays.append({
            'type': 'horizontal_line',
            'y': watch_zone_price,
            'color': 'orange',
            'width': 2,
            'dash': 'dot'
        })

        # Draw stop loss line (10% below 52-week low)
        stop_loss_price = week_52_low * 0.90
        overlays.append({
            'type': 'horizontal_line',
            'y': stop_loss_price,
            'color': 'darkred',
            'width': 2,
            'dash': 'dashdot'
        })

        # Add annotations
        last_date = stock_data.index[-1].strftime('%Y-%m-%d')
        annotations.extend([
            {
                'type': 'annotation',
                'x': last_date,
                'y': lifetime_high,
                'text': 'Lifetime High (Target)',
                'color': 'gold',
                'size': 12
            },
            {
                'type': 'annotation',
                'x': last_date,
                'y': week_52_low,
                'text': '52W Low (Entry)',
                'color': 'red',
                'size': 12
            },
            {
                'type': 'annotation',
                'x': last_date,
                'y': buy_zone_price,
                'text': 'Buy Zone (+5%)',
                'color': 'green',
                'size': 10
            },
            {
                'type': 'annotation',
                'x': last_date,
                'y': watch_zone_price,
                'text': 'Watch Zone (+10%)',
                'color': 'orange',
                'size': 10
            },
            {
                'type': 'annotation',
                'x': last_date,
                'y': stop_loss_price,
                'text': 'Stop Loss (-10%)',
                'color': 'darkred',
                'size': 10
            }
        ])

        # Mark current position
        annotations.append({
            'type': 'annotation',
            'x': last_date,
            'y': current_price,
            'text': 'Current Price',
            'color': 'blue',
            'size': 11,
            'bgcolor': 'lightblue'
        })

        # Add zones as shapes (optional - for better visualization)
        shapes = [
            {
                'type': 'rect',
                'x0': stock_data.index[0].strftime('%Y-%m-%d'),
                'x1': last_date,
                'y0': week_52_low,
                'y1': buy_zone_price,
                'fillcolor': 'rgba(0, 255, 0, 0.1)',
                'line': {'width': 0}
            },
            {
                'type': 'rect',
                'x0': stock_data.index[0].strftime('%Y-%m-%d'),
                'x1': last_date,
                'y0': buy_zone_price,
                'y1': watch_zone_price,
                'fillcolor': 'rgba(255, 165, 0, 0.1)',
                'line': {'width': 0}
            }
        ]

        return {
            'overlays': overlays,
            'annotations': annotations,
            'shapes': shapes
        }

    def _check_strategy_conditions(self, stock_data, fundamental_data=None):
        """Check if all strategy conditions are met"""
        conditions = {
            'qualified': False,
            'week_52_low': 0,
            'lifetime_high': 0,
            'distance_from_low': 0,
            'days_since_low': 0
        }

        # Calculate 52-week low (last 252 trading days)
        last_252_days = stock_data.tail(252)
        week_52_low = last_252_days['Low'].min()
        week_52_low_date = last_252_days['Low'].idxmin()

        # Calculate lifetime high
        lifetime_high = stock_data['High'].max()

        # Current price and distance calculations
        current_price = stock_data['Close'].iloc[-1]
        distance_from_low = (current_price - week_52_low) / week_52_low

        # Days since 52-week low
        days_since_low = (stock_data.index[-1] - week_52_low_date).days

        conditions.update({
            'week_52_low': week_52_low,
            'lifetime_high': lifetime_high,
            'distance_from_low': distance_from_low,
            'days_since_low': days_since_low
        })

        # Basic qualification - must have reasonable upside potential
        upside_potential = (lifetime_high - week_52_low) / week_52_low
        conditions['qualified'] = (
                upside_potential > 0.20 and  # Lowered from 30% to 20% for more flexibility
                lifetime_high > week_52_low * 1.15  # Lowered from 1.20 to 1.15
        )

        return conditions

    def _calculate_confidence(self, stock_data, conditions, fundamental_data):
        """Calculate confidence score for 52 Week Low strategy"""
        confidence = 30  # Base confidence

        # Distance from 52-week low (closer = higher confidence)
        distance = conditions['distance_from_low']
        if distance <= 0.02:  # Within 2% of 52W low
            confidence += 30
        elif distance <= 0.05:  # Within 5% of 52W low
            confidence += 25
        elif distance <= 0.10:  # Within 10% of 52W low
            confidence += 15
        elif distance <= 0.20:  # Within 20% of 52W low
            confidence += 10

        # Upside potential (higher potential = higher confidence)
        upside_potential = (conditions['lifetime_high'] - conditions['week_52_low']) / conditions['week_52_low']
        if upside_potential > 1.0:  # More than 100% upside
            confidence += 20
        elif upside_potential > 0.75:  # More than 75% upside
            confidence += 15
        elif upside_potential > 0.50:  # More than 50% upside
            confidence += 10
        elif upside_potential > 0.30:  # More than 30% upside
            confidence += 5

        # Recent volume activity (higher volume = more confidence)
        recent_volume = stock_data['Volume'].tail(10).mean()
        avg_volume = stock_data['Volume'].mean()
        if recent_volume > avg_volume * 1.5:
            confidence += 10
        elif recent_volume > avg_volume * 1.2:
            confidence += 5

        # Fundamental strength (if available)
        if fundamental_data:
            pe_ratio = fundamental_data.get('pe_ratio', 0)
            debt_to_equity = fundamental_data.get('debt_to_equity', 1)
            roe = fundamental_data.get('return_on_equity', 0)

            # Low valuation adds confidence
            if pe_ratio > 0 and pe_ratio < 15:  # Very reasonable P/E
                confidence += 10
            elif pe_ratio > 0 and pe_ratio < 25:  # Reasonable P/E
                confidence += 5

            # Strong balance sheet
            if debt_to_equity < 0.3:  # Very low debt
                confidence += 8
            elif debt_to_equity < 0.5:  # Low debt
                confidence += 5

            # Good profitability
            if roe > 0.20:  # Excellent ROE
                confidence += 7
            elif roe > 0.15:  # Good ROE
                confidence += 5

        # Days since 52-week low (recent lows might be more significant)
        days_since_low = conditions['days_since_low']
        if days_since_low <= 5:  # Very recent low
            confidence += 5
        elif days_since_low <= 30:  # Recent low
            confidence += 3

        return min(100, confidence)

    def _get_strategy_steps(self):
        """Get strategy implementation steps"""
        return [
            "1. Monitor quality stocks across all groups",
            "2. Identify stocks hitting or near their 52-week lows",
            "3. Verify reasonable upside potential (52W low to lifetime high > 20%)",
            "4. Enter buy signal when stock is within 5% of 52-week low",
            "5. Use 52-week low price as ideal entry point",
            "6. Set stop loss at 10% below 52-week low",
            "7. Primary target is always the lifetime high",
            "8. Allow averaging down if stock goes below entry",
            "9. Watch for volume confirmation during low formations",
            "10. Exit near lifetime high or if stop loss is triggered"
        ]