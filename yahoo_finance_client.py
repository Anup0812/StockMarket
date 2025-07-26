import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class YahooFinanceClient:
    def __init__(self):
        pass
    
    def get_stock_data(self, stock_code, period='1y'):
        """Fetch OHLCV data from Yahoo Finance"""
        try:
            # Add .NS suffix for NSE stocks if not already present
            if not stock_code.endswith('.NS'):
                symbol = f"{stock_code}.NS"
            else:
                symbol = stock_code
            
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            # Fetch historical data
            data = ticker.history(period=period)
            
            if data.empty:
                print(f"No data found for {symbol}")
                return pd.DataFrame()
            
            # Clean and prepare data
            data = data.dropna()
            
            return data
        except Exception as e:
            print(f"Error fetching stock data for {stock_code}: {e}")
            return pd.DataFrame()
    
    def get_fundamental_data(self, stock_code):
        """Fetch fundamental data from Yahoo Finance"""
        try:
            # Add .NS suffix for NSE stocks if not already present
            if not stock_code.endswith('.NS'):
                symbol = f"{stock_code}.NS"
            else:
                symbol = stock_code
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract relevant fundamental data
            fundamental_data = {
                'company_name': info.get('longName', 'N/A'),
                'industry_sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'current_price': info.get('currentPrice', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'week_52_high': info.get('fiftyTwoWeekHigh', 0),
                'week_52_low': info.get('fiftyTwoWeekLow', 0),
                'market_cap': info.get('marketCap', 0),
                'book_value': info.get('bookValue', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'profit_margins': info.get('profitMargins', 0),
                'operating_margins': info.get('operatingMargins', 0),
                'return_on_equity': info.get('returnOnEquity', 0),
                'return_on_assets': info.get('returnOnAssets', 0),
                'current_ratio': info.get('currentRatio', 0),
                'quick_ratio': info.get('quickRatio', 0),
                'business_summary': info.get('businessSummary', 'N/A'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Calculate lifetime high (approximate using available data)
            historical_data = ticker.history(period='max')
            if not historical_data.empty:
                fundamental_data['lifetime_high'] = historical_data['High'].max()
            else:
                fundamental_data['lifetime_high'] = fundamental_data['week_52_high']
            
            return fundamental_data
        except Exception as e:
            print(f"Error fetching fundamental data for {stock_code}: {e}")
            return {}
    
    def get_company_financials(self, stock_code):
        """Fetch detailed financial statements"""
        try:
            if not stock_code.endswith('.NS'):
                symbol = f"{stock_code}.NS"
            else:
                symbol = stock_code
            
            ticker = yf.Ticker(symbol)
            
            financials = {
                'income_statement': ticker.financials.to_dict() if hasattr(ticker, 'financials') else {},
                'balance_sheet': ticker.balance_sheet.to_dict() if hasattr(ticker, 'balance_sheet') else {},
                'cash_flow': ticker.cashflow.to_dict() if hasattr(ticker, 'cashflow') else {}
            }
            
            return financials
        except Exception as e:
            print(f"Error fetching financials for {stock_code}: {e}")
            return {}
