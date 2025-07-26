import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class SimpleMovingAverageStrategy(BaseStrategy):
    """Simple Moving Average Strategy for V40 companies"""

    def __init__(self):
        super().__init__()
        self.applicable_groups = ['V40']
        self.sma_periods = [20, 50, 200]

    def _calculate_sma_signal(self, stock_data):
        """
        Calculate Simple Moving Average signals based on strict AND conditions.
        This is the core signal generation method.
        """
        # Ensure there is enough data to calculate the longest SMA
        if len(stock_data) < 200:
            return {
                'signal': 'Neutral',
                'reason': 'Insufficient data for SMA calculation (less than 200 periods)',
                'sma_20': None, 'sma_50': None, 'sma_200': None,
                'current_price': stock_data['Close'].iloc[-1] if not stock_data.empty else 0,
                'current_sma_20': None,
                'current_sma_50': None,
                'current_sma_200': None,
                'price_sma_data': None
            }

        # Calculate SMAs
        sma_20 = self.calculate_sma(stock_data, 20)
        sma_50 = self.calculate_sma(stock_data, 50)
        sma_200 = self.calculate_sma(stock_data, 200)

        # Get the latest values for comparison
        current_price = stock_data['Close'].iloc[-1]
        current_sma_20 = sma_20.iloc[-1]
        current_sma_50 = sma_50.iloc[-1]
        current_sma_200 = sma_200.iloc[-1]

        # Create structured price and SMA data
        price_sma_data = {
            'current_price': round(current_price, 2),
            'sma_20_price': round(current_sma_20, 2),
            'sma_50_price': round(current_sma_50, 2),
            'sma_200_price': round(current_sma_200, 2),
            'price_vs_sma_20': round(((current_price - current_sma_20) / current_sma_20) * 100, 2),
            'price_vs_sma_50': round(((current_price - current_sma_50) / current_sma_50) * 100, 2),
            'price_vs_sma_200': round(((current_price - current_sma_200) / current_sma_200) * 100, 2)
        }


        # --- UPDATED LOGIC: Strict AND conditions as requested ---
        buy_condition = current_price < current_sma_20 < current_sma_50 < current_sma_200
        sell_condition = current_price > current_sma_20 > current_sma_50 > current_sma_200

        if buy_condition:
            signal = 'Buy'
            reason = 'Strong bearish alignment (Price < SMA20 < SMA50 < SMA200) - Contrarian Buy signal'
        elif sell_condition:
            signal = 'Sell'
            reason = 'Strong bullish alignment (Price > SMA20 > SMA50 > SMA200) - Contrarian Sell signal'
        else:
            signal = 'Neutral'
            reason = 'SMAs are not in the specific alignment for a Buy or Sell signal.'

        return {
            'signal': signal,
            'reason': reason,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'current_price': current_price,
            'current_sma_20': current_sma_20,
            'current_sma_50': current_sma_50,
            'current_sma_200': current_sma_200,
            'price_sma_data': price_sma_data
        }

    def get_signal(self, stock_data):
        """
        Get trading signal based on SMA conditions.
        This is a wrapper for the core logic to maintain compatibility.
        """
        signal_data = self._calculate_sma_signal(stock_data)
        return signal_data['signal']

    def get_price_sma_data(self, stock_data):
        """
        Get current price and SMA values in a structured format.
        This is a new method to easily access price and SMA data.
        """
        signal_data = self._calculate_sma_signal(stock_data)
        return signal_data['price_sma_data']

    def analyze_stock(self, stock_data, fundamental_data):
        """Perform detailed SMA analysis using the updated logic"""
        # Use the new method to get all calculated data and reasoning at once
        analysis = self._calculate_sma_signal(stock_data)

        # Exit if there's not enough data
        if analysis['sma_20'] is None:
            return None

        signal = analysis['signal']
        reason = analysis['reason']
        current_price = analysis['current_price']
        sma_20 = analysis['sma_20']

        # Calculate entry and target prices
        entry_price = current_price
        target_price = None

        if signal == 'Buy':
            # For a contrarian buy, a potential target could be the next resistance level (e.g., SMA20)
            target_price = sma_20.iloc[-1]
        elif signal == 'Sell':
            # For a contrarian sell, a potential target could be a support level (e.g., SMA20)
            target_price = sma_20.iloc[-1]

        # UPDATED: Strategy steps reflecting the new logic
        steps = [
            "1. Set up 20-day (Green), 50-day (Red), and 200-day (Blue) SMAs.",
            "2. Buy Signal: Price < 20 SMA < 50 SMA < 200 SMA (All conditions must be met).",
            "3. Sell Signal: Price > 20 SMA > 50 SMA > 200 SMA (All conditions must be met).",
            "4. This is a contrarian strategy: buying into a strong downtrend or selling into a strong uptrend.",
            "5. Use proper risk management with stop losses."
        ]

        # Signal details
        confidence = self._calculate_confidence(stock_data, analysis['sma_20'], analysis['sma_50'], analysis['sma_200'])
        signal_details = self.format_signal_details(signal, entry_price, target_price, confidence=confidence)

        # Add the detailed reason from our calculation
        signal_details['reason'] = reason

        # Add price and SMA data to signal details
        signal_details['price_sma_data'] = analysis['price_sma_data']

        return {
            'strategy_name': 'Simple Moving Average',
            'signal_details': signal_details,
            'steps': steps,
            'sma_data': {
                'sma_20': analysis['sma_20'].tolist(),
                'sma_50': analysis['sma_50'].tolist(),
                'sma_200': analysis['sma_200'].tolist()
            },
            'current_values': {
                'current_price': analysis['current_price'],
                'current_sma_20': analysis['current_sma_20'],
                'current_sma_50': analysis['current_sma_50'],
                'current_sma_200': analysis['current_sma_200']
            }
        }

    def get_chart_config(self, stock_data):
        """Get chart configuration with SMA overlays - Compatible with charts.js"""
        if len(stock_data) < 200:
            return {'overlays': [], 'annotations': []}

        try:
            sma_20 = self.calculate_sma(stock_data, 20)
            sma_50 = self.calculate_sma(stock_data, 50)
            sma_200 = self.calculate_sma(stock_data, 200)

            # Clean NaN values for JSON serialization
            sma_20_clean = sma_20.fillna(np.nan).replace({np.nan: None}).tolist()
            sma_50_clean = sma_50.fillna(np.nan).replace({np.nan: None}).tolist()
            sma_200_clean = sma_200.fillna(np.nan).replace({np.nan: None}).tolist()

            # Pad SMA data with None values for initial periods
            sma_20_padded = [None] * (len(stock_data) - len(sma_20_clean)) + sma_20_clean
            sma_50_padded = [None] * (len(stock_data) - len(sma_50_clean)) + sma_50_clean
            sma_200_padded = [None] * (len(stock_data) - len(sma_200_clean)) + sma_200_clean

            # UPDATED: Better colors for visibility
            overlays = [
                {
                    'type': 'line',
                    'name': 'SMA 20',
                    'data': sma_20_padded,
                    'color': '#00FF00',  # Bright green
                    'width': 2
                },
                {
                    'type': 'line',
                    'name': 'SMA 50',
                    'data': sma_50_padded,
                    'color': '#FF0000',  # Bright red
                    'width': 2
                },
                {
                    'type': 'line',
                    'name': 'SMA 200',
                    'data': sma_200_padded,
                    'color': '#0066FF',  # Blue instead of black for better visibility
                    'width': 3  # Thicker line for better visibility
                }
            ]

            # Get signal annotations
            annotations = self._get_signal_annotations(stock_data, sma_20, sma_50, sma_200)

            return {
                'overlays': overlays,
                'annotations': annotations
            }

        except Exception as e:
            print(f"Error in SMA chart config: {e}")
            return {'overlays': [], 'annotations': []}

    def _calculate_confidence(self, stock_data, sma_20, sma_50, sma_200):
        """Calculate confidence score for the signal"""
        try:
            current_price = stock_data['Close'].iloc[-1]

            # Check proper SMA alignment
            sma_alignment_score = 0
            # Alignment for buy signals
            if current_price < sma_20.iloc[-1] < sma_50.iloc[-1] < sma_200.iloc[-1]:
                sma_alignment_score = 30
            # Alignment for sell signals
            elif current_price > sma_20.iloc[-1] > sma_50.iloc[-1] > sma_200.iloc[-1]:
                sma_alignment_score = 30

            # Check volume confirmation
            volume_score = 20 if stock_data['Volume'].iloc[-1] > stock_data['Volume'].rolling(20).mean().iloc[
                -1] else 10

            # Check price position relative to SMAs
            price_position_score = 25 if sma_alignment_score > 0 else 0

            # Trend consistency
            trend_score = 25 if len(stock_data) > 10 else 0

            return min(100, sma_alignment_score + volume_score + price_position_score + trend_score)
        except Exception as e:
            print(f"Error calculating SMA confidence: {e}")
            return 50

    def _get_signal_annotations(self, stock_data, sma_20, sma_50, sma_200):
        """Get annotations for buy/sell signals"""
        try:
            annotations = []
            current_price = stock_data['Close'].iloc[-1]
            current_date = stock_data.index[-1]

            # We can still use the simple get_signal here as it's just for the annotation text
            signal = self.get_signal(stock_data)

            if signal in ['Buy', 'Sell']:
                annotations.append({
                    'type': 'annotation',
                    'x': current_date.strftime('%Y-%m-%d'),
                    'y': current_price,
                    'text': f'{signal} Signal',
                    'color': 'green' if signal == 'Buy' else 'red',
                    'size': 12
                })

            return annotations
        except Exception as e:
            print(f"Error creating SMA annotations: {e}")
            return []