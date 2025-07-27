import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class ReverseHeadShoulderStrategy(BaseStrategy):
    """Reverse Head and Shoulder Pattern Strategy - Enhanced with V10 detection logic and 15% gain requirement"""

    def __init__(self):
        super().__init__()
        self.applicable_groups = ['V40', 'V40_Next']
        self.min_gain_threshold = 0.15  # 15% minimum gain requirement

    def get_signal(self, stock_data):
        """Get trading signal based on RHS pattern with 15% gain requirement"""
        if len(stock_data) < 100:
            return 'Neutral'

        patterns = self._find_rhs_patterns(stock_data)

        if not patterns:
            return 'Neutral'

        current_price = stock_data['Close'].iloc[-1]

        for pattern in patterns:
            # Check potential gain first - must be at least 15%
            potential_gain = (pattern['target_price'] - current_price) / current_price
            if potential_gain < self.min_gain_threshold:
                continue  # Skip patterns with less than 15% gain

            # Check if we're at the right shoulder breakout point
            if self._is_breakout_confirmed(stock_data, pattern):
                return 'Buy'

            # Check if we're near the target (technical target only)
            if current_price >= pattern['target_price'] * 0.95:
                return 'Sell'

            # If pattern is forming but not confirmed (right shoulder base formation)
            if self._is_right_shoulder_base_forming(stock_data, pattern):
                return 'Watch'

        return 'Neutral'

    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed RHS analysis with 15% gain filtering"""
        if len(stock_data) < 100:
            return None

        all_patterns = self._find_rhs_patterns(stock_data)
        current_price = stock_data['Close'].iloc[-1]

        # Filter patterns by 15% gain requirement
        patterns = []
        for pattern in all_patterns:
            potential_gain = (pattern['target_price'] - current_price) / current_price
            if potential_gain >= self.min_gain_threshold:
                patterns.append(pattern)

        signal = self.get_signal(stock_data)

        if not patterns:
            # Check if there were any patterns before filtering
            rejected_reason = "No patterns with 15%+ gain potential" if all_patterns else "No valid RHS pattern identified"

            return {
                'strategy_name': 'Reverse Head and Shoulder (15% Gain Required)',
                'signal_details': self.format_signal_details('Neutral', current_price, None),
                'steps': self._get_strategy_steps(),
                'patterns': [],
                'rejected_patterns': len(all_patterns),
                'rejection_reason': rejected_reason
            }

        active_pattern = patterns[0]

        entry_price = current_price
        target_price = active_pattern['target_price']

        # Calculate confidence
        confidence = self._calculate_confidence(stock_data, active_pattern, fundamental_data)

        signal_details = self.format_signal_details(signal, entry_price, target_price, confidence=confidence)

        # Add reason and additional details
        if signal == 'Buy':
            signal_details[
                'reason'] = f"Green breakout candle confirmed above right shoulder base with {active_pattern['potential_gain']:.1f}% gain potential"
        elif signal == 'Sell':
            signal_details['reason'] = "Technical target price reached"
        elif signal == 'Watch':
            signal_details[
                'reason'] = f"Right shoulder base forming with {active_pattern['potential_gain']:.1f}% gain potential - wait for breakout confirmation"
        else:
            signal_details['reason'] = "No valid RHS pattern with 15%+ gain potential"

        signal_details['neckline'] = active_pattern['neckline']
        signal_details['pattern_depth'] = active_pattern['depth']
        signal_details['base_range'] = active_pattern.get('base_range', 'N/A')
        signal_details['neckline_horizontal_tolerance'] = active_pattern.get('neckline_tolerance', 'N/A')
        signal_details['min_gain_required'] = f"{self.min_gain_threshold * 100:.0f}%"
        signal_details['actual_gain_potential'] = f"{active_pattern['potential_gain']:.1f}%"

        return {
            'strategy_name': 'Reverse Head and Shoulder (15% Gain Required)',
            'signal_details': signal_details,
            'steps': self._get_strategy_steps(),
            'patterns': patterns,
            'active_pattern': active_pattern,
            'rejected_patterns': len(all_patterns) - len(patterns)
        }

    def get_chart_config(self, stock_data):
        """Get chart configuration with RHS pattern overlays"""
        if len(stock_data) < 100:
            return {}

        # Get all patterns first, then filter by gain requirement
        all_patterns = self._find_rhs_patterns(stock_data)
        current_price = stock_data['Close'].iloc[-1]

        patterns = []
        for pattern in all_patterns:
            potential_gain = (pattern['target_price'] - current_price) / current_price
            if potential_gain >= self.min_gain_threshold:
                patterns.append(pattern)

        if not patterns:
            return {}

        overlays = []
        annotations = []
        last_date_str = stock_data.index[-1].strftime('%Y-%m-%d')

        for pattern in patterns:
            # Draw RHS Pattern Outline - CORRECTED to show proper connection
            if all(k in pattern for k in ['left_shoulder', 'head', 'right_shoulder']):
                # Connect the three main pivot points in order
                pattern_points = [
                    pattern['left_shoulder'],
                    pattern['head'],
                    pattern['right_shoulder']
                ]

                x_coords = [p['date'].strftime('%Y-%m-%d') for p in pattern_points]
                y_coords = [p['price'] for p in pattern_points]

                overlays.append({
                    'type': 'scatter',
                    'x': x_coords,
                    'y': y_coords,
                    'mode': 'lines+markers',
                    'line': {'color': 'purple', 'width': 2},
                    'marker': {'color': 'purple', 'size': 8},
                    'name': f'RHS Pattern ({pattern["potential_gain"]:.1f}% gain)'
                })

            # Draw HORIZONTAL neckline - FIXED to be truly horizontal
            neckline_start = pattern['left_shoulder']['date'].strftime('%Y-%m-%d')
            neckline_end = last_date_str

            overlays.append({
                'type': 'scatter',
                'x': [neckline_start, neckline_end],
                'y': [pattern['neckline'], pattern['neckline']],
                'mode': 'lines',
                'line': {'color': 'blue', 'width': 2, 'dash': 'dash'},
                'name': 'Neckline'
            })

            # Draw target line (technical target only) - highlighted for 15%+ gain
            overlays.append({
                'type': 'scatter',
                'x': [neckline_start, neckline_end],
                'y': [pattern['target_price'], pattern['target_price']],
                'mode': 'lines',
                'line': {'color': 'green', 'width': 3, 'dash': 'dot'},  # Thicker line for qualified targets
                'name': f'Target (15%+ gain)'
            })

            # Draw base range as a rectangle
            if pattern.get('base_high') and pattern.get('base_low'):
                base_start_date = pattern['right_shoulder']['date'].strftime('%Y-%m-%d')
                overlays.append({
                    'type': 'rectangle',
                    'xref': 'x', 'yref': 'y',
                    'x0': base_start_date,
                    'y0': pattern['base_low'],
                    'x1': last_date_str,
                    'y1': pattern['base_high'],
                    'fillcolor': 'rgba(255, 165, 0, 0.2)',
                    'line': {'color': 'orange', 'width': 1}
                })

            # Mark key points with gain percentage
            points = [
                ('LS', pattern['left_shoulder']),
                ('H', pattern['head']),
                ('RS', pattern['right_shoulder'])
            ]

            for label, point in points:
                ay = 20 if label in ['LS', 'RS'] else -20  # Position below shoulders, above head
                annotations.append({
                    'x': point['date'].strftime('%Y-%m-%d'),
                    'y': point['price'],
                    'text': label,
                    'color': 'white',
                    'size': 12,
                    'ay': ay,
                    'ax': 0
                })

            # Add gain potential annotation
            annotations.append({
                'x': last_date_str,
                'y': pattern['target_price'],
                'text': f"+{pattern['potential_gain']:.1f}%",
                'color': 'green',
                'size': 14,
                'ay': -25,
                'ax': 0
            })

        return {
            'overlays': overlays,
            'annotations': annotations
        }

    def _find_rhs_patterns(self, stock_data):
        """Find Reverse Head and Shoulder patterns with enhanced V10-style detection"""
        patterns = []

        # Enhanced pivot detection using V10 style logic
        pivots = self._find_enhanced_pivot_lows(stock_data)

        if len(pivots) < 3:
            return patterns

        current_price = stock_data['Close'].iloc[-1]

        for i in range(len(pivots) - 2):
            left_shoulder = pivots[i]
            head = pivots[i + 1]
            right_shoulder = pivots[i + 2]

            if self._validate_rhs_pattern_enhanced(left_shoulder, head, right_shoulder, stock_data):
                # Calculate neckline as horizontal line connecting formation peaks
                neckline = self._calculate_horizontal_neckline_enhanced(left_shoulder, head, right_shoulder, stock_data)

                if neckline is None:
                    continue

                # Calculate depth from head to neckline
                depth = neckline - head['price']
                # Target is neckline + depth (technical target only)
                target_price = neckline + depth

                potential_gain = (target_price - current_price) / current_price
                base_info = self._detect_right_shoulder_base_enhanced(stock_data, right_shoulder)

                # Enhanced pattern validation with additional quality checks
                pattern_quality = self._assess_pattern_quality(left_shoulder, head, right_shoulder, stock_data)
                if pattern_quality < 0.6:  # Minimum quality threshold
                    continue

                pattern = {
                    'left_shoulder': left_shoulder,
                    'head': head,
                    'right_shoulder': right_shoulder,
                    'neckline': neckline,
                    'target_price': target_price,
                    'depth': depth,
                    'potential_gain': potential_gain * 100,
                    'pattern_start': left_shoulder['date'],
                    'pattern_end': right_shoulder['date'],
                    'base_range': f"{base_info['base_low']:.2f} - {base_info['base_high']:.2f}" if base_info else 'N/A',
                    'base_high': base_info['base_high'] if base_info else None,
                    'base_low': base_info['base_low'] if base_info else None,
                    'pattern_quality': pattern_quality,
                    'volume_confirmation': self._check_volume_pattern(stock_data, left_shoulder, head, right_shoulder),
                    'meets_gain_requirement': potential_gain >= self.min_gain_threshold
                }
                patterns.append(pattern)

        # Enhanced sorting considering quality, gain potential, and recency
        patterns.sort(
            key=lambda x: (x['meets_gain_requirement'], x['pattern_quality'], x['potential_gain'], x['pattern_end']),
            reverse=True)
        return patterns[:3]  # Return top 3 patterns

    def _find_enhanced_pivot_lows(self, stock_data, window=7):
        """Enhanced pivot low detection inspired by V10's significant high detection"""
        pivots = []

        # Use adaptive window size based on data length
        adaptive_window = max(5, min(window, len(stock_data) // 20))

        for i in range(adaptive_window, len(stock_data) - adaptive_window):
            current_low = stock_data['Low'].iloc[i]

            # Enhanced significance check - must be lowest in the window
            is_significant = True
            surrounding_lows = []

            for j in range(i - adaptive_window, i + adaptive_window + 1):
                if j != i:
                    surrounding_lows.append(stock_data['Low'].iloc[j])
                    if stock_data['Low'].iloc[j] <= current_low:
                        is_significant = False
                        break

            if is_significant:
                # Additional quality checks inspired by V10
                avg_surrounding = np.mean(surrounding_lows)
                significance_ratio = (avg_surrounding - current_low) / current_low

                # Only consider significant lows (at least 2% lower than average surrounding)
                if significance_ratio >= 0.02:
                    pivots.append({
                        'date': stock_data.index[i],
                        'price': current_low,
                        'index': i,
                        'significance': significance_ratio
                    })

        # Filter to only recent and significant pivots (like V10's time filtering)
        recent_date = stock_data.index[-1] - pd.Timedelta(days=365)  # 1 year lookback
        recent_pivots = [p for p in pivots if p['date'] >= recent_date]

        # Sort by significance and recency
        recent_pivots.sort(key=lambda x: (x['significance'], x['date']), reverse=True)

        return recent_pivots

    def _validate_rhs_pattern_enhanced(self, left_shoulder, head, right_shoulder, stock_data):
        """Enhanced RHS pattern validation with V10-inspired quality checks"""

        # Rule 1: Head must be deeper (lower) than both shoulders
        if not (head['price'] < left_shoulder['price'] and head['price'] < right_shoulder['price']):
            return False

        # Rule 2: Right shoulder CANNOT be deeper than head (strict requirement)
        if right_shoulder['price'] <= head['price']:
            return False

        # Rule 3: Enhanced pattern duration validation with adaptive ranges
        pattern_days = (right_shoulder['date'] - left_shoulder['date']).days
        if not (20 <= pattern_days <= 365):  # More flexible minimum duration
            return False

        # Rule 4: Chronological order validation
        if not (left_shoulder['date'] < head['date'] < right_shoulder['date']):
            return False

        # Enhanced Rule 5: Proportional spacing check (inspired by V10's gap logic)
        total_duration = pattern_days
        ls_to_head_days = (head['date'] - left_shoulder['date']).days
        head_to_rs_days = (right_shoulder['date'] - head['date']).days

        # Neither segment should be too short or too long relative to the total
        if ls_to_head_days < total_duration * 0.2 or ls_to_head_days > total_duration * 0.7:
            return False
        if head_to_rs_days < total_duration * 0.2 or head_to_rs_days > total_duration * 0.7:
            return False

        # Enhanced Rule 6: Depth significance check
        left_depth = (left_shoulder['price'] - head['price']) / head['price']
        right_depth = (right_shoulder['price'] - head['price']) / head['price']

        # Both shoulders should have meaningful depth from head (at least 3%)
        if left_depth < 0.03 or right_depth < 0.03:
            return False

        return True

    def _calculate_horizontal_neckline_enhanced(self, left_shoulder, head, right_shoulder, stock_data):
        """Enhanced neckline calculation with V10-inspired precision"""

        # Find the high point (rebound) after left shoulder but before head
        ls_to_head_data = stock_data.loc[left_shoulder['date']:head['date']]
        if len(ls_to_head_data) < 3:  # Need at least 3 data points
            return None

        # Enhanced peak detection - find the most significant high in the range
        ls_to_head_highs = ls_to_head_data['High'][1:-1]  # Exclude endpoints
        if len(ls_to_head_highs) == 0:
            return None

        # Find multiple candidate peaks and select the most significant
        peak1_candidates = []
        for i in range(1, len(ls_to_head_highs) - 1):
            if (ls_to_head_highs.iloc[i] > ls_to_head_highs.iloc[i - 1] and
                    ls_to_head_highs.iloc[i] > ls_to_head_highs.iloc[i + 1]):
                peak1_candidates.append((ls_to_head_highs.index[i], ls_to_head_highs.iloc[i]))

        if not peak1_candidates:
            peak1_idx = ls_to_head_highs.idxmax()
            peak1_price = ls_to_head_highs.max()
        else:
            # Select the highest among candidates
            peak1_idx, peak1_price = max(peak1_candidates, key=lambda x: x[1])

        # Find the high point (rebound) after head but before/at right shoulder
        head_to_rs_data = stock_data.loc[head['date']:right_shoulder['date']]
        if len(head_to_rs_data) < 3:
            return None

        # Enhanced peak detection for second peak
        head_to_rs_highs = head_to_rs_data['High'][1:-1]  # Exclude endpoints
        if len(head_to_rs_highs) == 0:
            return None

        peak2_candidates = []
        for i in range(1, len(head_to_rs_highs) - 1):
            if (head_to_rs_highs.iloc[i] > head_to_rs_highs.iloc[i - 1] and
                    head_to_rs_highs.iloc[i] > head_to_rs_highs.iloc[i + 1]):
                peak2_candidates.append((head_to_rs_highs.index[i], head_to_rs_highs.iloc[i]))

        if not peak2_candidates:
            peak2_idx = head_to_rs_highs.idxmax()
            peak2_price = head_to_rs_highs.max()
        else:
            # Select the highest among candidates
            peak2_idx, peak2_price = max(peak2_candidates, key=lambda x: x[1])

        # Enhanced horizontal validation with adaptive tolerance
        if min(peak1_price, peak2_price) == 0:
            return None

        price_diff_pct = abs(peak1_price - peak2_price) / min(peak1_price, peak2_price)

        # Adaptive tolerance based on volatility (inspired by V10's confidence calculation)
        recent_volatility = stock_data['Close'].pct_change().tail(50).std()
        tolerance = max(0.015, min(0.03, recent_volatility * 2))  # 1.5% to 3% based on volatility

        if price_diff_pct > tolerance:
            return None

        # Calculate horizontal neckline as weighted average (give more weight to more recent peak)
        weight1, weight2 = 0.4, 0.6  # Recent peak gets more weight
        neckline = (peak1_price * weight1 + peak2_price * weight2)

        # Validate neckline is above head
        if neckline <= head['price']:
            return None

        return neckline

    def _detect_right_shoulder_base_enhanced(self, stock_data, right_shoulder):
        """Enhanced base detection with V10-inspired logic"""
        start_idx = right_shoulder['index']

        # Adaptive lookforward period based on pattern timeframe
        lookforward_days = min(30, len(stock_data) - start_idx - 1)
        end_idx = min(start_idx + lookforward_days, len(stock_data))
        recent_data = stock_data.iloc[start_idx:end_idx]

        if len(recent_data) < 5:
            return None

        base_high = recent_data['High'].max()
        base_low = recent_data['Low'].min()

        if base_low == 0:
            return None

        range_pct = (base_high - base_low) / base_low

        # Enhanced base validation with volume consideration
        base_volume = recent_data['Volume'].mean() if 'Volume' in recent_data.columns else 0
        overall_volume = stock_data['Volume'].mean() if 'Volume' in stock_data.columns else 1

        volume_ratio = base_volume / overall_volume if overall_volume > 0 else 1

        # Adaptive range threshold based on stock volatility
        recent_volatility = stock_data['Close'].pct_change().tail(50).std()
        max_range = max(0.04, min(0.08, recent_volatility * 3))  # 4% to 8% based on volatility

        # Base should be tight consolidation with reasonable volume
        if range_pct <= max_range and volume_ratio >= 0.7:  # At least 70% of average volume
            return {
                'base_high': base_high,
                'base_low': base_low,
                'range_pct': range_pct * 100,
                'volume_ratio': volume_ratio,
                'quality_score': (1 - range_pct / max_range) * volume_ratio
            }
        return None

    def _assess_pattern_quality(self, left_shoulder, head, right_shoulder, stock_data):
        """Assess overall pattern quality inspired by V10's confidence calculation"""
        quality_score = 0.5  # Base quality

        # Symmetry check
        left_depth = left_shoulder['price'] - head['price']
        right_depth = right_shoulder['price'] - head['price']
        symmetry_ratio = min(left_depth, right_depth) / max(left_depth, right_depth) if max(left_depth,
                                                                                            right_depth) > 0 else 0
        quality_score += symmetry_ratio * 0.2

        # Time symmetry
        ls_to_head_days = (head['date'] - left_shoulder['date']).days
        head_to_rs_days = (right_shoulder['date'] - head['date']).days
        time_symmetry = min(ls_to_head_days, head_to_rs_days) / max(ls_to_head_days, head_to_rs_days) if max(
            ls_to_head_days, head_to_rs_days) > 0 else 0
        quality_score += time_symmetry * 0.15

        # Depth significance
        total_depth = left_shoulder['price'] - head['price']
        depth_significance = min(total_depth / head['price'], 0.25) / 0.25  # Cap at 25%
        quality_score += depth_significance * 0.15

        return min(1.0, quality_score)

    def _check_volume_pattern(self, stock_data, left_shoulder, head, right_shoulder):
        """Enhanced volume pattern analysis inspired by V10"""
        if 'Volume' not in stock_data.columns:
            return False

        try:
            # Volume during pattern formation
            pattern_data = stock_data.loc[left_shoulder['date']:right_shoulder['date']]
            pattern_volume = pattern_data['Volume'].mean()

            # Overall average volume
            overall_volume = stock_data['Volume'].mean()

            # Volume should be above average during pattern formation
            return pattern_volume > overall_volume * 0.9  # At least 90% of average
        except:
            return False

    def _is_breakout_confirmed(self, stock_data, pattern):
        """Enhanced breakout confirmation with V10-inspired precision"""
        recent_data = stock_data.tail(5)  # Look at more recent data
        base_info = self._detect_right_shoulder_base_enhanced(stock_data, pattern['right_shoulder'])

        if base_info is None:
            return False

        # Enhanced breakout detection
        breakout_confirmed = False
        volume_support = False

        for _, row in recent_data.iterrows():
            # Green candle: Close > Open AND Close > base_high with margin
            if (row['Close'] > row['Open'] and
                    row['Close'] > base_info['base_high'] * 1.005):  # 0.5% margin above base
                breakout_confirmed = True

                # Check volume support if available
                if 'Volume' in recent_data.columns:
                    recent_avg_volume = stock_data['Volume'].tail(20).mean()
                    if row['Volume'] > recent_avg_volume * 0.8:  # At least 80% of recent average
                        volume_support = True
                break

        return breakout_confirmed and (volume_support or 'Volume' not in stock_data.columns)

    def _is_right_shoulder_base_forming(self, stock_data, pattern):
        """Enhanced base formation detection"""
        base_info = self._detect_right_shoulder_base_enhanced(stock_data, pattern['right_shoulder'])
        if base_info is None:
            return False

        recent_price = stock_data['Close'].iloc[-1]

        # Price should be within the base range with some tolerance
        base_center = (base_info['base_high'] + base_info['base_low']) / 2
        base_range = base_info['base_high'] - base_info['base_low']

        # Allow some tolerance around the base range
        tolerance = base_range * 0.1  # 10% tolerance
        return (base_info['base_low'] - tolerance <= recent_price <=
                base_info['base_high'] + tolerance)

    def _calculate_confidence(self, stock_data, pattern, fundamental_data):
        """Enhanced confidence calculation with V10-inspired factors and gain bonus"""
        confidence = 50  # Reduced base confidence, will be built up

        # Pattern quality (max 25 points)
        quality_score = pattern.get('pattern_quality', 0.6)
        confidence += int(quality_score * 25)

        # Pattern depth significance (max 20 points)
        depth_ratio = (pattern['neckline'] - pattern['head']['price']) / pattern['head']['price']
        if depth_ratio > 0.20:  # Very deep head
            confidence += 20
        elif depth_ratio > 0.15:
            confidence += 17
        elif depth_ratio > 0.10:
            confidence += 13
        elif depth_ratio > 0.05:
            confidence += 8

        # Base formation quality (max 20 points)
        base_info = self._detect_right_shoulder_base_enhanced(stock_data, pattern['right_shoulder'])
        if base_info:
            quality_score = base_info.get('quality_score', 0.5)
            confidence += int(quality_score * 20)

        # Volume confirmation (max 15 points)
        if pattern.get('volume_confirmation', False):
            confidence += 15

        # Gain potential bonus (max 15 points) - NEW
        gain_pct = pattern['potential_gain'] / 100
        if gain_pct >= 0.30:  # 30%+ gain
            confidence += 15
        elif gain_pct >= 0.25:  # 25%+ gain
            confidence += 12
        elif gain_pct >= 0.20:  # 20%+ gain
            confidence += 9
        elif gain_pct >= 0.15:  # 15%+ gain (minimum requirement)
            confidence += 6

        # Pattern timing and recency (max 10 points)
        pattern_days = (pattern['pattern_end'] - pattern['pattern_start']).days
        if 45 <= pattern_days <= 120:  # Optimal duration
            confidence += 10
        elif 30 <= pattern_days <= 150:
            confidence += 7
        elif 20 <= pattern_days <= 200:
            confidence += 4

        # Recent pattern bonus (max 10 points)
        days_since_rs = (stock_data.index[-1] - pattern['right_shoulder']['date']).days
        if days_since_rs <= 30:
            confidence += 10
        elif days_since_rs <= 60:
            confidence += 7
        elif days_since_rs <= 90:
            confidence += 4

        return min(100, int(confidence))

    def _get_strategy_steps(self):
        """Get enhanced strategy implementation steps with 15% gain requirement"""
        return [
            "1. Identify significant pivot lows using enhanced detection (2%+ significance)",
            "2. Find three pivots: Left Shoulder, Head (deepest), Right Shoulder",
            "3. Validate: Head deeper than both shoulders, right shoulder NOT deeper than head",
            "4. Check proportional spacing and depth significance (3%+ from head)",
            "5. Find rebound peaks after left shoulder and after head formations",
            "6. Draw horizontal neckline with adaptive tolerance (1.5-3% based on volatility)",
            "7. Calculate technical target: Neckline + (Neckline - Head depth)",
            "8. FILTER: Only consider patterns with 15%+ gain potential from current price",
            "9. Assess overall pattern quality (symmetry, timing, depth)",
            "10. Wait for right shoulder to form enhanced base (4-8% range based on volatility)",
            "11. Look for confirmed breakout with volume support above base range",
            "12. Buy on breakout confirmation with 0.5% margin above base (15%+ gain assured)",
            "13. Monitor for technical target achievement"
        ]