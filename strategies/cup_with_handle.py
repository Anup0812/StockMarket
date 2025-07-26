import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class CupWithHandleStrategy(BaseStrategy):
    """Cup with Handle Strategy"""

    def __init__(self):
        super().__init__()
        self.applicable_groups = ['V40', 'V40_Next']
        self.min_gain_threshold = 0.40  # 40% minimum potential gain for lifetime high patterns

    def get_signal(self, stock_data):
        """Get trading signal based on Cup with Handle pattern"""
        if len(stock_data) < 100:
            return 'Neutral'

        patterns = self._find_cwh_patterns(stock_data)

        if not patterns:
            return 'Neutral'

        current_price = stock_data['Close'].iloc[-1]

        for pattern in patterns:
            # Check if we're at the handle breakout point
            if self._is_breakout_confirmed(stock_data, pattern):
                return 'Buy'

            # Check if we're near the target (sell at technical target only)
            if current_price >= pattern['target_price'] * 0.95:
                return 'Sell'

            # Check for negative potential gain (sell when loss occurs)
            if self._has_negative_potential_gain(stock_data, pattern):
                return 'Sell'

            # If pattern is forming but not confirmed
            if self._is_pattern_forming(stock_data, pattern):
                return 'Watch'

        return 'Neutral'

    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed Cup with Handle analysis"""
        if len(stock_data) < 100:
            return None

        patterns = self._find_cwh_patterns(stock_data)
        current_price = stock_data['Close'].iloc[-1]
        signal = self.get_signal(stock_data)

        if not patterns:
            return {
                'strategy_name': 'Cup with Handle',
                'signal_details': self.format_signal_details('Neutral', current_price, None),
                'steps': self._get_strategy_steps(),
                'patterns': []
            }

        active_pattern = patterns[0]

        entry_price = current_price
        target_price = active_pattern['target_price']

        # Calculate confidence
        confidence = self._calculate_confidence(stock_data, active_pattern, fundamental_data)

        signal_details = self.format_signal_details(signal, entry_price, target_price, confidence=confidence)

        # Add reason and additional details
        if signal == 'Buy':
            signal_details['reason'] = "Breakout confirmed from handle base formation"
        elif signal == 'Sell':
            if current_price >= active_pattern['target_price'] * 0.95:
                signal_details['reason'] = "Technical target reached"
            else:
                signal_details['reason'] = "Negative potential gain detected - stop loss triggered"
        elif signal == 'Watch':
            signal_details['reason'] = "Cup with Handle pattern forming, waiting for breakout"
        else:
            signal_details['reason'] = "No valid Cup with Handle pattern identified"

        signal_details['cup_depth'] = active_pattern['cup_depth']
        signal_details['handle_depth'] = active_pattern.get('handle_depth', 0)
        signal_details['pattern_type'] = active_pattern['cup_type']

        return {
            'strategy_name': 'Cup with Handle',
            'signal_details': signal_details,
            'steps': self._get_strategy_steps(),
            'patterns': patterns,
            'active_pattern': active_pattern
        }

    def get_chart_config(self, stock_data):
        """Get chart configuration with Cup with Handle pattern overlays"""
        if len(stock_data) < 100:
            return {}

        patterns = self._find_cwh_patterns(stock_data)

        overlays = []
        annotations = []

        for pattern in patterns:
            # Draw cup outline
            cup_points = pattern['cup_points']
            if len(cup_points) >= 3:
                x_coords = [point['date'].strftime('%Y-%m-%d') for point in cup_points]
                y_coords = [point['price'] for point in cup_points]

                overlays.append({
                    'type': 'scatter',
                    'x': x_coords,
                    'y': y_coords,
                    'mode': 'lines',
                    'line': {'color': 'blue', 'width': 2},
                    'name': 'Cup'
                })

            # Draw handle if present
            if 'handle_points' in pattern and pattern['handle_points']:
                handle_points = pattern['handle_points']
                x_coords = [point['date'].strftime('%Y-%m-%d') for point in handle_points]
                y_coords = [point['price'] for point in handle_points]

                overlays.append({
                    'type': 'scatter',
                    'x': x_coords,
                    'y': y_coords,
                    'mode': 'lines',
                    'line': {'color': 'orange', 'width': 2},
                    'name': 'Handle'
                })

            # Draw neckline
            overlays.append({
                'type': 'horizontal_line',
                'y': pattern['neckline'],
                'color': 'purple',
                'width': 2,
                'dash': 'dash'
            })

            # Draw target line
            overlays.append({
                'type': 'horizontal_line',
                'y': pattern['target_price'],
                'color': 'green',
                'width': 2,
                'dash': 'dot'
            })

            # Add annotations
            annotations.extend([
                {
                    'type': 'annotation',
                    'x': pattern['cup_start']['date'].strftime('%Y-%m-%d'),
                    'y': pattern['cup_start']['price'],
                    'text': 'Cup Start',
                    'color': 'blue',
                    'size': 10
                },
                {
                    'type': 'annotation',
                    'x': pattern['cup_bottom']['date'].strftime('%Y-%m-%d'),
                    'y': pattern['cup_bottom']['price'],
                    'text': 'Cup Bottom',
                    'color': 'blue',
                    'size': 10
                }
            ])

        return {
            'overlays': overlays,
            'annotations': annotations
        }

    def _find_cwh_patterns(self, stock_data):
        """Find Cup with Handle patterns"""
        patterns = []

        # Find potential cup formations
        cup_candidates = self._find_cup_formations(stock_data)

        for cup in cup_candidates:
            # Look for handle formation after cup
            handle = self._find_handle_formation(stock_data, cup)

            # Calculate neckline and target (technical target only)
            neckline = cup['neckline']
            cup_depth = neckline - cup['cup_bottom']['price']
            target_price = neckline + cup_depth  # Only use technical target

            pattern = {
                'cup_start': cup['cup_start'],
                'cup_bottom': cup['cup_bottom'],
                'cup_end': cup['cup_end'],
                'cup_type': cup['cup_type'],
                'cup_depth': cup_depth,
                'cup_points': cup['cup_points'],
                'neckline': neckline,
                'target_price': target_price,  # Technical target only
                'pattern_start': cup['cup_start']['date'],
                'pattern_end': cup['cup_end']['date']
            }

            if handle:
                pattern['handle_start'] = handle['handle_start']
                pattern['handle_end'] = handle['handle_end']
                pattern['handle_depth'] = handle['handle_depth']
                pattern['handle_points'] = handle['handle_points']
                pattern['pattern_end'] = handle['handle_end']['date']

            patterns.append(pattern)

        # Sort by recency and pattern quality
        patterns.sort(key=lambda x: x['pattern_end'], reverse=True)

        return patterns[:2]  # Return top 2 patterns

    def _find_cup_formations(self, stock_data):
        """Find cup formations (U-shaped or V-shaped with proper recovery)"""
        cups = []

        # Use the same logic as V10 strategy for finding significant highs
        highs = self._find_significant_highs(stock_data)

        for i, start_high in enumerate(highs):
            for j, end_high in enumerate(highs[i + 1:], i + 1):
                # Check neckline variance (max 1% as per rule)
                neckline_variance = abs(start_high['price'] - end_high['price']) / start_high['price']
                if neckline_variance > 0.01:  # 1% threshold
                    continue

                # Calculate neckline as average of both highs
                neckline = (start_high['price'] + end_high['price']) / 2

                # Find the lowest point between the two highs
                cup_data = stock_data.loc[start_high['date']:end_high['date']]
                if len(cup_data) < 20:  # Minimum cup duration
                    continue

                bottom_idx = cup_data['Low'].idxmin()
                bottom_price = cup_data.loc[bottom_idx, 'Low']

                # Check cup depth (minimum 15%)
                cup_depth = neckline - bottom_price
                cup_depth_percent = cup_depth / neckline
                if cup_depth_percent < 0.15:  # Minimum 15% depth
                    continue

                # Check recovery requirement (minimum 80%)
                recovery = end_high['price'] - bottom_price
                total_decline = neckline - bottom_price
                recovery_percent = recovery / total_decline
                if recovery_percent < 0.80:  # Minimum 80% recovery
                    continue

                # Determine cup type and create points
                cup_type, cup_points = self._determine_cup_type(cup_data, start_high, end_high, bottom_idx,
                                                                bottom_price)

                cup = {
                    'cup_start': start_high,
                    'cup_bottom': {'date': bottom_idx, 'price': bottom_price},
                    'cup_end': end_high,
                    'cup_type': cup_type,
                    'cup_points': cup_points,
                    'cup_depth': cup_depth,
                    'neckline': neckline
                }

                cups.append(cup)

        return cups

    def _find_handle_formation(self, stock_data, cup):
        """Find handle formation after cup with base consolidation check"""
        # Look for data after cup end
        cup_end_date = cup['cup_end']['date']
        after_cup = stock_data.loc[cup_end_date:]

        if len(after_cup) < 10:  # Minimum handle duration
            return None

        # Handle should not be bigger than cup (max 50% of cup depth)
        max_handle_depth = cup['cup_depth'] * 0.5

        # Find potential handle formation
        handle_data = after_cup.head(min(50, len(after_cup)))  # Look at next 50 days max

        # Simple handle detection: find a pullback and recovery
        handle_start = cup['cup_end']
        handle_low_idx = handle_data['Low'].idxmin()
        handle_low_price = handle_data.loc[handle_low_idx, 'Low']

        handle_depth = handle_start['price'] - handle_low_price

        if handle_depth > max_handle_depth:
            return None  # Handle too deep

        # Check for base formation (consolidation < 5% range)
        base_data = handle_data.loc[handle_low_idx:]
        if len(base_data) < 5:
            return None

        # Look for base consolidation period
        base_period = base_data.head(10)  # Check last 10 days for base
        base_high = base_period['High'].max()
        base_low = base_period['Low'].min()
        base_range = (base_high - base_low) / base_low

        if base_range > 0.05:  # Base range should be < 5%
            return None

        # Find handle end (recovery point)
        for date, row in base_data.iterrows():
            if row['High'] >= handle_start['price'] * 0.95:  # Within 5% of handle start
                handle_end = {'date': date, 'price': row['High']}

                # Create handle points
                handle_points = [
                    handle_start,
                    {'date': handle_low_idx, 'price': handle_low_price},
                    handle_end
                ]

                return {
                    'handle_start': handle_start,
                    'handle_end': handle_end,
                    'handle_depth': handle_depth,
                    'handle_points': handle_points
                }

        return None

    def _find_significant_highs(self, stock_data, window=5):
        """Find significant high points using V10 strategy logic for better accuracy"""
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

    def _determine_cup_type(self, cup_data, start_high, end_high, bottom_idx, bottom_price):
        """Determine cup type (U-shaped or V-shaped) and create points for drawing"""
        # Sample key points for cup drawing
        cup_points = [start_high]

        # Add intermediate points based on cup type
        mid_date = cup_data.index[len(cup_data) // 2]
        mid_price = cup_data.loc[mid_date, 'Close']

        # Determine if it's U-shaped or V-shaped
        bottom_to_mid_ratio = (mid_price - bottom_price) / (start_high['price'] - bottom_price)

        if bottom_to_mid_ratio > 0.3:
            cup_type = "U-shaped"
        else:
            cup_type = "V-shaped"

        # Add bottom point
        cup_points.append({'date': bottom_idx, 'price': bottom_price})

        # Add end point
        cup_points.append(end_high)

        return cup_type, cup_points

    def _is_breakout_confirmed(self, stock_data, pattern):
        """Check if breakout from handle/cup is confirmed with green closing candle"""
        recent_data = stock_data.tail(5)
        neckline = pattern['neckline']

        # Check for green candle closing above neckline
        for _, row in recent_data.iterrows():
            if (row['Close'] > row['Open'] and  # Green candle
                    row['Close'] > neckline):  # Above neckline
                return True

        return False

    def _is_pattern_forming(self, stock_data, pattern):
        """Check if pattern is still forming"""
        current_date = stock_data.index[-1]
        pattern_age = (current_date - pattern['pattern_end']).days

        # Pattern is forming if it's recent and not yet broken out
        return pattern_age <= 30 and not self._is_breakout_confirmed(stock_data, pattern)

    def _calculate_confidence(self, stock_data, pattern, fundamental_data):
        """Calculate confidence score for Cup with Handle pattern"""
        confidence = 50  # Base confidence

        # Cup depth (deeper cups are more reliable)
        cup_depth_percent = pattern['cup_depth'] / pattern['neckline'] * 100
        if cup_depth_percent > 30:
            confidence += 20
        elif cup_depth_percent > 20:
            confidence += 15
        elif cup_depth_percent > 15:
            confidence += 10

        # Handle presence and quality
        if 'handle_depth' in pattern:
            confidence += 15  # Handle present
            handle_ratio = pattern['handle_depth'] / pattern['cup_depth']
            if handle_ratio < 0.3:  # Good handle depth ratio
                confidence += 10

        # Cup type (U-shaped is most reliable)
        if pattern['cup_type'] == "U-shaped":
            confidence += 15
        elif pattern['cup_type'] == "V-shaped":
            confidence += 10

        # Volume confirmation
        pattern_start = pattern['pattern_start']
        pattern_end = pattern['pattern_end']
        pattern_volume = stock_data.loc[pattern_start:pattern_end]['Volume'].mean()
        overall_volume = stock_data['Volume'].mean()
        if pattern_volume > overall_volume:
            confidence += 5

        return min(100, confidence)

    def _has_negative_potential_gain(self, stock_data, pattern):
        """Check if potential gain is negative (current price below breakout/entry level)"""
        current_price = stock_data['Close'].iloc[-1]

        # Use neckline as reference entry point
        entry_reference = pattern['neckline']

        # If current price is below entry reference, potential gain is negative
        potential_gain = (current_price - entry_reference) / entry_reference

        return potential_gain < -0.02  # Trigger sell if loss exceeds 2%

    def _get_strategy_steps(self):
        """Get strategy implementation steps"""
        return [
            "1. Identify cup formation: U-shaped or V-shaped decline (min 15%) + recovery (min 80%)",
            "2. Look for handle formation after cup (optional but preferred)",
            "3. Handle must be smaller than cup depth (max 50%)",
            "4. Neckline connects cup highs (max 1% variance)",
            "5. Handle forms a base (consolidation < 5% range)",
            "6. Wait for breakout above base with green closing candle",
            "7. Buy next day (or at closing) after breakout confirmation",
            "8. Calculate target: Neckline + Cup depth",
            "9. Sell at technical target",
        ]