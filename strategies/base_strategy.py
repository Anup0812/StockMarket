from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.applicable_groups = []
    
    @abstractmethod
    def get_signal(self, stock_data):
        """
        Get trading signal for given stock data
        Returns: 'Buy', 'Sell', 'Watch', or 'Neutral'
        """
        pass
    
    @abstractmethod
    def analyze_stock(self, stock_data, fundamental_data):
        """
        Perform detailed analysis of a stock
        Returns: Dictionary with analysis results
        """
        pass
    
    @abstractmethod
    def get_chart_config(self, stock_data):
        """
        Get chart configuration with overlays and annotations
        Returns: Dictionary with Plotly chart configuration
        """
        pass
    
    def is_applicable_to_group(self, group):
        """Check if strategy is applicable to a stock group"""
        if not self.applicable_groups:
            return True  # If no specific groups defined, apply to all
        return group in self.applicable_groups
    
    def calculate_sma(self, data, period):
        """Calculate Simple Moving Average"""
        return data['Close'].rolling(window=period).mean()
    
    def calculate_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        return data['Close'].ewm(span=period).mean()
    
    def calculate_rsi(self, data, period=14):
        """Calculate Relative Strength Index"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def find_support_resistance(self, data, window=20):
        """Find support and resistance levels"""
        highs = data['High'].rolling(window=window, center=True).max()
        lows = data['Low'].rolling(window=window, center=True).min()
        
        resistance_levels = data[data['High'] == highs]['High'].drop_duplicates()
        support_levels = data[data['Low'] == lows]['Low'].drop_duplicates()
        
        return support_levels.tolist(), resistance_levels.tolist()
    
    def calculate_pattern_validity(self, data, pattern_start, pattern_end):
        """Calculate the validity score of a pattern"""
        pattern_data = data[pattern_start:pattern_end]
        if len(pattern_data) < 10:
            return 0
        
        # Basic validity checks
        volatility = pattern_data['Close'].std() / pattern_data['Close'].mean()
        volume_consistency = pattern_data['Volume'].mean() > 0
        
        return min(100, max(0, (1 - volatility) * 100)) if volume_consistency else 0
    
    def get_pattern_coordinates(self, data, pattern_points):
        """Get coordinates for drawing pattern lines"""
        coordinates = []
        for point in pattern_points:
            if point['date'] in data.index:
                coordinates.append({
                    'date': point['date'].strftime('%Y-%m-%d'),
                    'price': point['price'],
                    'type': point.get('type', 'point')
                })
        return coordinates
    
    def format_signal_details(self, signal, entry_price, target_price, stop_loss=None, confidence=0):
        """Format signal details for display"""
        if target_price and entry_price:
            potential_gain = ((target_price - entry_price) / entry_price) * 100
        else:
            potential_gain = 0
        
        return {
            'signal': signal,
            'entry_price': round(entry_price, 2) if entry_price else 0,
            'target_price': round(target_price, 2) if target_price else 0,
            'stop_loss': round(stop_loss, 2) if stop_loss else None,
            'potential_gain': round(potential_gain, 2),
            'confidence': round(confidence, 2)
        }
