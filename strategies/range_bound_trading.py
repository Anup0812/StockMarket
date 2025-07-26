import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class RangeBoundTradingStrategy(BaseStrategy):
    """Range-Bound Trading Strategy with FIXED validation for proper alternating pairs"""

    def __init__(self):
        super().__init__()
        self.min_range_size = 0.14  # 14% minimum range
        self.preferred_range_size = 0.20  # 20% preferred range
        self.tolerance = 0.02  # 2% tolerance for entries
        self.min_touches = 2
        self.min_historical_data = 60  # Minimum 60 days of data

    def get_signal(self, stock_data):
        """Get trading signal based on range-bound conditions"""
        if len(stock_data) < self.min_historical_data:
            return 'Neutral'

        # Use the FIXED range detection logic
        result = self.calculate_range_bound_signal(stock_data)
        return result.get('signal', 'Neutral')

    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed range-bound analysis with FIXED validation."""
        if len(stock_data) < self.min_historical_data:
            return {
                'strategy_name': 'Range-Bound Trading',
                'signal_details': self.format_signal_details('Neutral',
                                                             stock_data['Close'].iloc[-1] if len(stock_data) > 0 else 0,
                                                             None),
                'steps': self._get_strategy_steps(),
                'ranges': [],
                'error': f'Insufficient historical data. Need at least {self.min_historical_data} days.'
            }

        # Use the FIXED analysis function
        result = self.calculate_range_bound_signal(stock_data)
        signal = result.get('signal', 'Neutral')
        current_price = result.get('current_price', stock_data['Close'].iloc[-1])
        support_level = result.get('support_level')
        resistance_level = result.get('resistance_level')

        entry_price = current_price

        # Target price will be resistance price
        target_price = resistance_level  # Set target price to resistance level if available

        potential_gain = None
        # Calculate potential gain based on the signal
        if signal == 'Buy' and current_price and current_price > 0 and resistance_level:
            # For a 'Buy' signal, calculate gain from current price to resistance
            potential_gain = ((resistance_level - current_price) / current_price) * 100
        elif signal == 'Watch' and support_level and support_level > 0 and resistance_level:
            # For a 'Watch' signal, calculate gain from support to resistance
            potential_gain = ((resistance_level - support_level) / support_level) * 100

        confidence = 60  # Base confidence
        if signal == 'Buy':
            confidence = min(100, confidence + 25)
        elif signal == 'Sell':
            confidence = min(100, confidence + 25)
        elif signal == 'Watch':
            confidence = min(100, confidence + 15)

        signal_details = self.format_signal_details(signal, entry_price, target_price, confidence=confidence)
        signal_details['reason'] = result.get('reasoning', 'No valid range-bound pattern identified')

        # Add potential gain and target price to the signal details
        if potential_gain is not None:
            signal_details['potential_gain'] = f'{potential_gain:.2f}%'

        if target_price is not None:
            signal_details['target_price'] = round(target_price, 2)

        # Convert result to legacy format for compatibility
        ranges = []
        if result.get('support_level') and result.get('resistance_level'):
            ranges = [{
                'support': result['support_level'],
                'resistance': result['resistance_level'],
                'range_size_percent': result.get('range_percent', 0),
                'support_touches': result.get('support_touches', 0),
                'resistance_touches': result.get('resistance_touches', 0),
                'total_touches': result.get('support_touches', 0) + result.get('resistance_touches', 0)
            }]

        return {
            'strategy_name': 'Range-Bound Trading',
            'signal_details': signal_details,
            'steps': self._get_strategy_steps(),
            'ranges': ranges,
            'active_range': ranges[0] if ranges else None,
            'range_details': result  # Add full result for debugging
        }

    def calculate_range_bound_signal(self, hist_data, min_touches=2, min_range_pct=14.0, preferred_range_pct=20.0):
        """
        FIXED: Detects Range Bound zones with proper validation for minimum touches as pairs
        """
        # 1. Initial Data Validation
        if len(hist_data) < 60:
            return {
                'signal': 'NEUTRAL',
                'reasoning': 'Insufficient data for Range Bound analysis (minimum 60 days required).'
            }

        current_price = hist_data['Close'].iloc[-1]
        # Use more data for better range detection (last 12 months)
        data = hist_data.tail(252) if len(hist_data) >= 252 else hist_data

        # 2. Enhanced Pivot Point Detection
        def find_pivot_highs(prices, window=5):
            """Find pivot highs with smaller window for better sensitivity"""
            pivots = []
            for i in range(window, len(prices) - window):
                if prices.iloc[i] == prices.iloc[i - window:i + window + 1].max():
                    pivots.append(i)
            return pivots

        def find_pivot_lows(prices, window=5):
            """Find pivot lows with smaller window for better sensitivity"""
            pivots = []
            for i in range(window, len(prices) - window):
                if prices.iloc[i] == prices.iloc[i - window:i + window + 1].min():
                    pivots.append(i)
            return pivots

        # Find resistance and support pivots with multiple window sizes
        resistance_indices = []
        support_indices = []

        # Use multiple window sizes to catch different timeframe pivots
        for window in [5, 8, 12]:
            resistance_indices.extend(find_pivot_highs(data['High'], window=window))
            support_indices.extend(find_pivot_lows(data['Low'], window=window))

        # Remove duplicates and sort
        resistance_indices = sorted(list(set(resistance_indices)))
        support_indices = sorted(list(set(support_indices)))

        if len(support_indices) < min_touches or len(resistance_indices) < min_touches:
            return {
                'signal': 'NEUTRAL',
                'current_price': current_price,
                'reasoning': f'Not enough pivot points found (S:{len(support_indices)}, R:{len(resistance_indices)}). Minimum {min_touches} each required.'
            }

        # 3. Find Multiple Valid Range Combinations
        def cluster_levels(prices, indices, tolerance=0.025):
            """Cluster nearby price levels together with tighter tolerance"""
            if not indices:
                return []

            price_levels = [prices.iloc[i] for i in indices]
            clusters = []

            for price in price_levels:
                added_to_cluster = False
                for cluster in clusters:
                    if abs(price - cluster['center']) / cluster['center'] <= tolerance:
                        cluster['prices'].append(price)
                        cluster['center'] = np.mean(cluster['prices'])
                        cluster['count'] += 1
                        added_to_cluster = True
                        break

                if not added_to_cluster:
                    clusters.append({
                        'center': price,
                        'prices': [price],
                        'count': 1
                    })

            # Sort by count (most touched levels first)
            clusters.sort(key=lambda x: x['count'], reverse=True)
            return clusters

        # Cluster support and resistance levels
        support_clusters = cluster_levels(data['Low'], support_indices)
        resistance_clusters = cluster_levels(data['High'], resistance_indices)

        if not support_clusters or not resistance_clusters:
            return {
                'signal': 'NEUTRAL',
                'current_price': current_price,
                'reasoning': 'Could not identify clustered support/resistance levels.'
            }

        # 4. FIXED: Find Best Range with Strict Validation
        best_range = None
        best_score = 0

        # Try different combinations of support and resistance levels
        for s_cluster in support_clusters[:3]:  # Top 3 support clusters
            for r_cluster in resistance_clusters[:3]:  # Top 3 resistance clusters
                support_level = s_cluster['center']
                resistance_level = r_cluster['center']

                # Ensure proper order
                if resistance_level <= support_level:
                    continue

                # Calculate range percentage
                range_percent = ((resistance_level - support_level) / support_level) * 100

                # Skip if range is too small
                if range_percent < min_range_pct:
                    continue

                # FIXED: Strict alternating pattern validation
                alternating_touches = self.validate_strict_alternating_pattern(
                    data, support_level, resistance_level
                )

                # FIXED: Count actual alternating touches, not just any touches
                support_touch_count = sum(1 for touch in alternating_touches if touch[0] == 'Support')
                resistance_touch_count = sum(1 for touch in alternating_touches if touch[0] == 'Resistance')

                # FIXED: Strict validation - must have minimum touches AND proper alternating pattern
                if (support_touch_count < min_touches or
                        resistance_touch_count < min_touches or
                        len(alternating_touches) < (min_touches * 2)):  # At least 2 complete cycles
                    continue

                # FIXED: Validate that we have proper pairs (alternating pattern)
                if not self.has_proper_alternating_pairs(alternating_touches, min_touches):
                    continue

                # Calculate score (higher is better)
                score = (
                        range_percent * 0.4 +  # Prefer larger ranges
                        (support_touch_count + resistance_touch_count) * 10 +  # More touches = better
                        (s_cluster['count'] + r_cluster['count']) * 5  # More clustered pivots = better
                )

                if score > best_score:
                    best_score = score
                    best_range = {
                        'support_level': support_level,
                        'resistance_level': resistance_level,
                        'range_percent': range_percent,
                        'support_touches': support_touch_count,
                        'resistance_touches': resistance_touch_count,
                        'alternating_touches': alternating_touches,
                        'support_cluster_strength': s_cluster['count'],
                        'resistance_cluster_strength': r_cluster['count']
                    }

        # FIXED: Proper rejection if no valid range found
        if not best_range:
            return {
                'signal': 'NEUTRAL',
                'current_price': current_price,
                'reasoning': f'No valid range found meeting ALL criteria: min {min_range_pct}% range, {min_touches} touches each level AS PAIRS, and proper alternating pattern.'
            }

        # Extract best range details
        support_level = best_range['support_level']
        resistance_level = best_range['resistance_level']
        range_percent = best_range['range_percent']
        support_touch_count = best_range['support_touches']
        resistance_touch_count = best_range['resistance_touches']
        alternating_touches = best_range['alternating_touches']

        range_quality = "STRONG" if range_percent >= preferred_range_pct else "ACCEPTABLE"

        # 5. Generate Trading Signal
        # Define tolerance zones for entry signals
        support_tolerance = support_level * 0.02  # 2% tolerance
        resistance_tolerance = resistance_level * 0.02  # 2% tolerance

        buy_zone_upper = support_level + support_tolerance
        sell_zone_lower = resistance_level - resistance_tolerance

        # Determine signal
        if current_price <= buy_zone_upper:
            signal = 'Buy'
            reasoning = f'Price near Support Level ({support_level:.2f}). Buy opportunity with valid alternating pattern.'
        elif current_price >= sell_zone_lower:
            signal = 'Sell'
            reasoning = f'Price near Resistance Level ({resistance_level:.2f}). Sell opportunity with valid alternating pattern.'
        else:
            signal = 'Watch'
            reasoning = f'Price within range ({support_level:.2f} - {resistance_level:.2f}). Watch for levels with valid alternating pattern.'

        # 6. Return Comprehensive Result
        return {
            'signal': signal,
            'current_price': round(current_price, 2),
            'support_level': round(support_level, 2),
            'resistance_level': round(resistance_level, 2),
            'range_percent': round(range_percent, 2),
            'range_quality': range_quality,
            'support_touches': support_touch_count,
            'resistance_touches': resistance_touch_count,
            'alternating_pattern': ' → '.join([touch[0] for touch in alternating_touches]),
            'recent_touches': [
                f"{touch[0]}: {touch[1].strftime('%Y-%m-%d')} at {touch[2]:.2f}"
                for touch in alternating_touches[-6:]  # Show last 6 touches
            ],
            'support_cluster_strength': best_range['support_cluster_strength'],
            'resistance_cluster_strength': best_range['resistance_cluster_strength'],
            'trading_levels': {
                'buy_zone_upper': round(buy_zone_upper, 2),
                'sell_zone_lower': round(sell_zone_lower, 2),
                'support_tolerance': round(support_tolerance, 2),
                'resistance_tolerance': round(resistance_tolerance, 2)
            },
            'reasoning': reasoning,
            'pattern_validation': f'Valid alternating pattern with {len(alternating_touches)} total touches ({support_touch_count}S + {resistance_touch_count}R)'
        }

    def validate_strict_alternating_pattern(self, data, support_level, resistance_level, tolerance=0.03):
        """
        FIXED: Strict alternating pattern validation that enforces proper Support→Resistance→Support pattern
        """
        touches = []

        # Define threshold levels
        support_threshold = support_level * (1 + tolerance)  # Support can be touched at or below this level
        resistance_threshold = resistance_level * (1 - tolerance)  # Resistance can be touched at or above this level

        for i in range(len(data)):
            low = data['Low'].iloc[i]
            high = data['High'].iloc[i]
            date = data.index[i]

            # Check for support touch (prioritize support if both conditions met)
            if low <= support_threshold:
                touches.append(('Support', date, low, i))
            # Check for resistance touch (only if support not touched)
            elif high >= resistance_threshold:
                touches.append(('Resistance', date, high, i))

        # FIXED: Enforce strict alternating pattern - remove consecutive touches of same type
        filtered_touches = []
        last_type = None

        for touch in touches:
            if touch[0] != last_type:
                filtered_touches.append(touch)
                last_type = touch[0]

        return filtered_touches

    def has_proper_alternating_pairs(self, alternating_touches, min_touches):
        """
        FIXED: Validate that we have proper alternating pairs
        """
        if len(alternating_touches) < (min_touches * 2):
            return False

        # Check if pattern truly alternates (no consecutive same types)
        for i in range(1, len(alternating_touches)):
            if alternating_touches[i][0] == alternating_touches[i - 1][0]:
                return False  # Same type consecutive - not alternating

        # Count complete pairs
        support_count = sum(1 for touch in alternating_touches if touch[0] == 'Support')
        resistance_count = sum(1 for touch in alternating_touches if touch[0] == 'Resistance')

        # Both support and resistance must have minimum touches
        return support_count >= min_touches and resistance_count >= min_touches

    def get_chart_config(self, stock_data):
        """Get chart configuration with range overlays"""
        if len(stock_data) < self.min_historical_data:
            return {}

        # Get range details from the FIXED analysis
        result = self.calculate_range_bound_signal(stock_data)

        overlays = []
        annotations = []

        if result.get('support_level') and result.get('resistance_level'):
            # Draw support and resistance lines
            overlays.extend([
                {
                    'type': 'horizontal_line',
                    'y': result['support_level'],
                    'color': 'green',
                    'width': 3,
                    'dash': 'solid'
                },
                {
                    'type': 'horizontal_line',
                    'y': result['resistance_level'],
                    'color': 'red',
                    'width': 3,
                    'dash': 'solid'
                }
            ])

            # Add range zone highlighting
            start_date = stock_data.index[0]
            end_date = stock_data.index[-1]

            overlays.append({
                'type': 'rectangle',
                'x0': start_date.strftime('%Y-%m-%d'),
                'y0': result['support_level'],
                'x1': end_date.strftime('%Y-%m-%d'),
                'y1': result['resistance_level'],
                'fillcolor': 'rgba(128,128,128,0.1)',
                'line': {
                    'color': 'gray',
                    'width': 1,
                    'dash': 'dot'
                }
            })

            # FIXED: Add touch points visualization
            if 'alternating_touches' in result:
                for touch in result['alternating_touches']:
                    color = 'green' if touch[0] == 'Support' else 'red'
                    annotations.append({
                        'x': touch[1].strftime('%Y-%m-%d'),
                        'y': touch[2],
                        'text': f"{touch[0]}<br>{touch[2]:.2f}",
                        'showarrow': True,
                        'arrowcolor': color,
                        'arrowsize': 1,
                        'arrowwidth': 2,
                        'font': {'size': 10, 'color': color},
                        'bgcolor': 'rgba(255,255,255,0.8)',
                        'bordercolor': color,
                        'borderwidth': 1
                    })

        return {
            'overlays': overlays,
            'annotations': annotations
        }

    def _calculate_confidence(self, stock_data, range_data):
        """Calculate confidence score for range-bound signal"""
        confidence = 40  # Base confidence

        # Range size (larger ranges are better, preferred ≥20%)
        if range_data['range_size_percent'] >= self.preferred_range_size * 100:
            confidence += 25
        elif range_data['range_size_percent'] >= self.min_range_size * 100:
            confidence += 15

        # Number of touches (more touches = higher confidence)
        touch_score = min(20, range_data['total_touches'] * 3)
        confidence += touch_score

        # Current price validation (within or near range)
        current_price = stock_data['Close'].iloc[-1]
        if (range_data['support'] <= current_price <= range_data['resistance'] or
                abs(current_price - range_data['support']) / current_price <= self.tolerance or
                abs(current_price - range_data['resistance']) / current_price <= self.tolerance):
            confidence += 10

        return min(100, confidence)

    def _get_strategy_steps(self):
        """Get FIXED strategy implementation steps"""
        return [
            "1. Use daily charts only to identify clear support and resistance levels",
            "2. Ensure each level is touched at least 2 times AS ALTERNATING PAIRS",
            "3. Verify STRICT alternating pattern: Support → Resistance → Support → Resistance",
            "4. Confirm minimum 14% range size (preferred 20%+)",
            "5. Check for clear zig-zag movement between levels with NO consecutive same-level touches",
            "6. Ensure sufficient historical data (≥60 days)",
            "7. REJECT patterns that don't have proper alternating pairs",
            "8. BUY near support level (within 2% tolerance) ONLY with valid pattern",
            "9. SELL near resistance level (within 2% tolerance) ONLY with valid pattern",
            "10. WATCH and monitor if price is inside the range with valid pattern",
            "11. Return NEUTRAL if alternating pair requirements not met"
        ]