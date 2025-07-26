import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class V20Strategy(BaseStrategy):
    """V20 Strategy - 20% movement identification with strict green candle rules"""

    def __init__(self):
        super().__init__()
        self.applicable_groups = ['V40', 'V40_Next', 'V200']
        self.movement_threshold = 0.20  # 20% movement
        self.max_age_months = 12  # Only consider patterns within last 12 months
        self.averaging_gap = 0.10  # 10% gap for averaging down

    def get_signal(self, stock_data):
        """Get trading signal based on V20 conditions"""
        if len(stock_data) < 30:
            return 'Neutral'

        # Find valid 20% green candle patterns
        patterns = self._find_20_percent_green_movements(stock_data)

        if not patterns:
            return 'Neutral'

        current_price = stock_data['Close'].iloc[-1]

        # Check most recent valid pattern
        for pattern in patterns:
            lower_line = pattern['bottom']  # Lower line from green sequence
            upper_line = pattern['top']  # Upper line from green sequence

            # Buy signal: when price touches or goes below lower line
            if current_price <= lower_line * 1.02:  # 2% tolerance
                return 'Buy'

            # Sell signal: when price reaches upper line
            if current_price >= upper_line * 0.98:  # 2% tolerance
                return 'Sell'

            # Watch signal: price is within the range
            if lower_line < current_price < upper_line:
                return 'Watch'

        return 'Neutral'

    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed V20 analysis"""
        if len(stock_data) < 30:
            return None

        patterns = self._find_20_percent_green_movements(stock_data)
        current_price = stock_data['Close'].iloc[-1]
        signal = self.get_signal(stock_data)

        if not patterns:
            return {
                'strategy_name': 'V20 Strategy',
                'signal_details': self.format_signal_details('Neutral', current_price, None),
                'steps': self._get_strategy_steps(),
                'patterns': []
            }

        # Use the most recent valid pattern
        active_pattern = patterns[0]

        entry_price = current_price
        target_price = active_pattern['top'] if signal == 'Buy' else None

        # Calculate confidence based on pattern strength
        confidence = self._calculate_confidence(stock_data, active_pattern)

        signal_details = self.format_signal_details(signal, entry_price, target_price, confidence=confidence)

        # Add detailed reason based on the rules
        lower_line = active_pattern['bottom']
        upper_line = active_pattern['top']

        if signal == 'Buy':
            signal_details['reason'] = f"Price at/below lower line (₹{lower_line:.2f}) of 20% green movement range"
        elif signal == 'Sell':
            signal_details['reason'] = f"Price reached upper line (₹{upper_line:.2f}) of 20% green movement range"
        elif signal == 'Watch':
            signal_details['reason'] = f"Price within 20% green movement range (₹{lower_line:.2f} - ₹{upper_line:.2f})"
        else:
            signal_details['reason'] = "No valid 20% green candle movement pattern found in last 12 months"

        return {
            'strategy_name': 'V20 Strategy',
            'signal_details': signal_details,
            'steps': self._get_strategy_steps(),
            'patterns': patterns,
            'active_pattern': active_pattern
        }

    def get_chart_config(self, stock_data):
        """Get chart configuration with V20 pattern overlays"""
        if len(stock_data) < 30:
            return {}

        patterns = self._find_20_percent_green_movements(stock_data)

        overlays = []
        annotations = []

        for i, pattern in enumerate(patterns):
            # Draw range lines (lower and upper)
            overlays.extend([
                {
                    'type': 'line_segment',  # CHANGED from 'line'
                    'x0': pattern['start_date'].strftime('%Y-%m-%d'),
                    'x1': pattern['end_date'].strftime('%Y-%m-%d'),
                    'y0': pattern['bottom'],
                    'y1': pattern['bottom'],
                    'line': {'color': 'green', 'width': 2, 'dash': 'solid'},
                    'name': f'Lower Line {i + 1}'
                },
                {
                    'type': 'line_segment',  # CHANGED from 'line'
                    'x0': pattern['start_date'].strftime('%Y-%m-%d'),
                    'x1': pattern['end_date'].strftime('%Y-%m-%d'),
                    'y0': pattern['top'],
                    'y1': pattern['top'],
                    'line': {'color': 'red', 'width': 2, 'dash': 'solid'},
                    'name': f'Upper Line {i + 1}'
                }
            ])

            # Add annotations for the pattern
            annotations.extend([
                {
                    'type': 'annotation',
                    'x': pattern['start_date'].strftime('%Y-%m-%d'),
                    'y': pattern['bottom'],
                    'text': f'Buy Line {i + 1}',
                    'color': 'green',
                    'size': 10
                },
                {
                    'type': 'annotation',
                    'x': pattern['end_date'].strftime('%Y-%m-%d'),
                    'y': pattern['top'],
                    'text': f'Sell Line {i + 1}',
                    'color': 'red',
                    'size': 10
                }
            ])

        return {
            'overlays': overlays,
            'annotations': annotations
        }

    def _find_20_percent_green_movements(self, stock_data):
        """Find valid 20% green candle movements according to the rules"""
        patterns = []

        try:
            # Only consider data from last 12 months
            twelve_months_ago = stock_data.index[-1] - pd.DateOffset(months=self.max_age_months)
            recent_data = stock_data[stock_data.index >= twelve_months_ago].copy()

            if len(recent_data) < 10:
                return patterns

            # Identify green candles (Close > Open)
            recent_data['is_green'] = recent_data['Close'] > recent_data['Open']

            i = 0
            while i < len(recent_data) - 1:
                if recent_data.iloc[i]['is_green']:
                    # Start of potential green sequence
                    sequence_start = i
                    sequence_end = i

                    # Extend sequence while candles are green (no red candles allowed)
                    j = i + 1
                    while j < len(recent_data) and recent_data.iloc[j]['is_green']:
                        sequence_end = j
                        j += 1

                    # Calculate movement from lowest to highest in the sequence
                    sequence_data = recent_data.iloc[sequence_start:sequence_end + 1]
                    lowest_point = sequence_data['Low'].min()
                    highest_point = sequence_data['High'].max()

                    # Check if movement is >= 20%
                    if lowest_point > 0:  # Avoid division by zero
                        movement_percent = ((highest_point - lowest_point) / lowest_point) * 100

                        if movement_percent >= (self.movement_threshold * 100):
                            # Find exact dates for lowest and highest points
                            lowest_idx = sequence_data['Low'].idxmin()
                            highest_idx = sequence_data['High'].idxmax()

                            pattern = {
                                'start_date': recent_data.index[sequence_start],
                                'end_date': recent_data.index[sequence_end],
                                'bottom': lowest_point,  # Lower line
                                'top': highest_point,  # Upper line
                                'movement_percent': movement_percent,
                                'duration_days': (
                                            recent_data.index[sequence_end] - recent_data.index[sequence_start]).days,
                                'green_candle_count': sequence_end - sequence_start + 1,
                                'lowest_date': lowest_idx,
                                'highest_date': highest_idx
                            }

                            patterns.append(pattern)

                    # Move to end of current sequence
                    i = sequence_end + 1
                else:
                    i += 1

                # Limit patterns to avoid performance issues
                if len(patterns) >= 10:
                    break

        except Exception as e:
            print(f"Error in V20 green movement pattern finding: {e}")
            return []

        # Sort by recency and movement percentage
        patterns.sort(key=lambda x: (x['end_date'], x['movement_percent']), reverse=True)

        return patterns[:5]  # Return top 5 most relevant patterns

    def _calculate_confidence(self, stock_data, pattern):
        """Calculate confidence score for V20 signal"""
        confidence = 50  # Base confidence

        # Movement percentage (higher is better)
        if pattern['movement_percent'] > 30:
            confidence += 25
        elif pattern['movement_percent'] > 25:
            confidence += 20
        elif pattern['movement_percent'] > 20:
            confidence += 15

        # Recency (more recent is better)
        days_old = (stock_data.index[-1] - pattern['end_date']).days
        if days_old < 30:
            confidence += 20
        elif days_old < 90:
            confidence += 15
        elif days_old < 180:
            confidence += 10

        # Number of green candles in sequence (more is better)
        if pattern['green_candle_count'] >= 5:
            confidence += 15
        elif pattern['green_candle_count'] >= 3:
            confidence += 10
        elif pattern['green_candle_count'] >= 2:
            confidence += 5

        # Duration of pattern (reasonable duration is better)
        if 5 <= pattern['duration_days'] <= 30:
            confidence += 10
        elif 1 <= pattern['duration_days'] <= 60:
            confidence += 5

        return min(100, max(0, confidence))

    def _get_strategy_steps(self):
        """Get strategy implementation steps according to the rules"""
        return [
            "1. Identify green candles or consecutive green candles with no red candles in between",
            "2. Measure total movement from lowest point to highest point in the green sequence",
            "3. Ensure the movement is ≥20% and occurred within last 12 months",
            "4. Define Lower Line: Lowest point of the green candle sequence",
            "5. Define Upper Line: Highest point of the green candle sequence",
            "6. Buy when stock retraces and touches the lower line",
            "7. If price falls ≥10% below first buy, average down",
            "8. Sell when stock rises back to the upper line for profit",
            "9. Each range is independent—wait for new 20% green movement after completion"
        ]

    def get_averaging_signal(self, stock_data, last_buy_price):
        """Check if averaging down is recommended (≥10% below last buy)"""
        if last_buy_price is None:
            return False

        current_price = stock_data['Close'].iloc[-1]
        price_drop_percent = ((last_buy_price - current_price) / last_buy_price) * 100

        return price_drop_percent >= (self.averaging_gap * 100)