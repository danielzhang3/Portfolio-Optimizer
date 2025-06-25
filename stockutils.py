from django.core.cache import cache
from decimal import Decimal
import yfinance as yf
import yahooquery as yq
from datetime import datetime, timedelta

# Cache expiry time for prices
price_cache_expiry = 3600 * 2  # 1 hour in seconds
all_time_high_cache_expiry = 3600 * 24 * 7
price_by_date_cache_expiry = 86400 * 2

# Index ticker mapping
INDEX_TICKERS = {"XND": "^XND", "MYM": "MYM=F", "YM": "YM=F", "ES": "ES=F", "SPX": "^SPX", "XSP": "^XSP", "DJX": "^DJX"}

IGNORE_LIST = {"ESHIX", "ESMAX", "MSKE.TA", "ESM.TO", "NQMLF", "ESUD.L"}

def get_ticker_symbol(company_name):
    if company_name in IGNORE_LIST: 
        return None
    
    if company_name in INDEX_TICKERS:
        return INDEX_TICKERS[company_name]

    # Check cache first
    ticker = cache.get(f"ticker_{company_name}")
    if ticker:
        return ticker

    # Search using yahooquery
    search = yq.search(company_name)
    quotes = search.get('quotes')
    if quotes:
        ticker = quotes[0]['symbol']
        cache.set(f"ticker_{company_name}", ticker, timeout=price_cache_expiry)
        return ticker
    return None

def fetch_latest_stock_price(company_name):
    try:
        ticker = get_ticker_symbol(company_name)
        if not ticker:
            return Decimal('0.0')  # or another default value

        cached_price = cache.get(f"price_{ticker}")
        if cached_price:
            return Decimal(cached_price)

        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        
        # If no data is returned, try a 2-day period to pick up Friday's close
        if data.empty:
            print(f"No 1d data for {ticker}. Trying 5-day history...")
            data = stock.history(period="5d")
            if data.empty:
                print(f"No 5-day data for {ticker}. Returning 0.0.")
                return Decimal('0.0')
        
        latest_price = data['Close'].iloc[-1]  # Most recent close price
        price = Decimal(str(latest_price))
        cache.set(f"price_{ticker}", str(price), timeout=price_cache_expiry)
        return price

    except ValueError as ve:
        print(f"ValueError fetching data for {company_name}: {ve}")
        return Decimal('0.0')
    except Exception as e:
        print(f"Error fetching data for {company_name}: {e}")
        return Decimal('0.0')

def fetch_all_time_high(company_name):
    try:
        ticker = get_ticker_symbol(company_name)
        if not ticker:
            return Decimal('0.0')  # or another default value

        cached_all_time_high = cache.get(f"all_time_high_{ticker}")
        if cached_all_time_high:
            return Decimal(cached_all_time_high)

        # Special handling for ^XND since 'max' is not a valid period for it
        period = 'max' if ticker != '^XND' else '5d'

        # Fetch historical data to calculate all-time high
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)  # Adjust period based on ticker
        if not data.empty:
            all_time_high = data['High'].max()  # Find the max value in the 'High' column
            price = Decimal(str(all_time_high))
            cache.set(f"all_time_high_{ticker}", str(price), timeout=all_time_high_cache_expiry)
            return price
        else:
            return Decimal('0.0')  # handle no data case

    except ValueError as ve:
        print(f"ValueError fetching all-time high for {company_name}: {ve}")
        return Decimal('0.0')
    except Exception as e:
        print(f"Error fetching all-time high for {company_name}: {e}")
        return Decimal('0.0')

def fetch_stock_price_by_date(company_name, date_str):
    try:
        # Get the ticker symbol (uses your existing get_ticker_symbol function)
        ticker = get_ticker_symbol(company_name)
        if not ticker:
            return Decimal('0.0')
        
        # Build a cache key using ticker and date_str
        cache_key = f"price_by_date_{ticker}_{date_str}"
        cached_price = cache.get(cache_key)
        if cached_price is not None:
            return Decimal(cached_price)
        
        # Convert the date string to a datetime object
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # Set the start date and end date (end date must be 1 day ahead since it's exclusive)
        start_date = date_str
        end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Fetch historical data for the date range with auto_adjust set to False
        stock = yf.Ticker(ticker)
        data = stock.history(start=start_date, end=end_date, auto_adjust=False)
        
        if data.empty:
            print(f"No data returned for {ticker} on {date_str}")
            return Decimal('0.0')
        
        # Explicitly select the raw 'Close' column (ignoring 'Adj Close')
        if 'Close' in data.columns:
            close_price = data['Close'].iloc[0]
        else:
            # Fallback if for some reason 'Close' is not available.
            close_price = data.iloc[0]
        
        price = Decimal(str(close_price))
        # Cache the price for 24 hours
        cache.set(cache_key, str(price), timeout=price_by_date_cache_expiry)
        return price
    
    except Exception as e:
        print(f"Error fetching stock price for {company_name} on {date_str}: {e}")
        return Decimal('0.0')
