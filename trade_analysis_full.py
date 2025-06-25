import re
import calendar
from datetime import datetime, timedelta, date
from decimal import Decimal
import pandas as pd
import logging
from api.utils.stock_utils import fetch_latest_stock_price, fetch_stock_price_by_date, get_ticker_symbol
from api.models import Trade, Trade_History, ATHSubmission
from django.db.models import Min

# Regular expressions
NUMBER_AND_LETTER_PATTERN = re.compile(
    r'(\d{2}[A-Z]{3}\d{2}|\d{2}/\d{2}/\d{4}|\d{2}\d{2}\d{4})\s+(\d+\.*\d*)\s*([CP])'
)
STOCK_SYMBOL_PATTERN = re.compile(r"([A-Z&\s]+)")

# Extraction helpers
def extract_number_and_letter(option_string: str):
    match = NUMBER_AND_LETTER_PATTERN.search(option_string)
    if match:
        return match.group(2), match.group(3)
    return None, None

def extract_stock_symbol(option_string: str):
    match = STOCK_SYMBOL_PATTERN.match(option_string)
    return match.group(1).strip() if match else None

def extract_expiration_date(stock_name: str):
    match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', stock_name)
    if match:
        try:
            return datetime.strptime(match.group(1), "%m/%d/%Y")
        except ValueError:
            pass
    match = re.search(r'\b(\d{2}[A-Z]{3}\d{2})\b', stock_name)
    if match:
        try:
            return datetime.strptime(match.group(1), "%d%b%y")
        except ValueError:
            pass
    return None

def is_short_term(expiration_date, threshold_days=5):
    return (expiration_date - datetime.now()).days < threshold_days

def third_friday(year: int, month: int) -> datetime:
    month_cal = calendar.monthcalendar(year, month)
    return datetime(year, month, month_cal[2][calendar.FRIDAY] if month_cal[0][calendar.FRIDAY] else month_cal[3][calendar.FRIDAY])

FUTURES_TICKER_MAPPING = {
    "ESH": "ESH25.CME", "ESM": "ESM25.CME", "ESU": "ESU25.CME", "ESZ": "ESZ25.CME",
    "MESH": "MESH25.CME", "MESM": "MESM25.CME", "MESU": "MESU25.CME", "MESZ": "MESZ25.CME",
    "NQH": "NQH25.CME", "NQM": "NQM25.CME", "NQU": "NQU25.CME", "NQZ": "NQZ25.CME",
    "MNQH": "MNQH25.CME", "MNQM": "MNQM25.CME", "MNQU": "MNQU25.CME", "MNQZ": "MNQZ25.CME",
    "YMH": "YMH25.CME", "YMM": "YMM25.CME", "YMU": "YMU25.CME", "YMZ": "YMZ25.CME",
    "MYMH": "MYMH25.CBT", "MYMM": "MYMM25.CBT", "MYMU": "MYMU25.CBT", "MYMZ": "MYMZ25.CBT",
    "RTYH": "RTYH25.CME", "RTYM": "RTYM25.CME", "RTYU": "RTYU25.CME", "RTYZ": "RTYZ25.CME",
}

def normalize_stock_symbol(symbol: str) -> str:
    symbol_clean = symbol.strip().lstrip('$').upper()
    return FUTURES_TICKER_MAPPING.get(symbol_clean, symbol_clean)

def get_multiplier(multiplier_dict: dict, stock_symbol: str):
    if stock_symbol in multiplier_dict:
        return multiplier_dict[stock_symbol]
    return next((m for sym, m in multiplier_dict.items() if sym in stock_symbol), None)

# Price caching
CACHE_TIMEOUT = timedelta(seconds=3600)
GLOBAL_PRICE_CACHE = {}

def get_price_cached(ticker: str) -> Decimal:
    now = datetime.now()
    if ticker in GLOBAL_PRICE_CACHE:
        cached_price, expiry = GLOBAL_PRICE_CACHE[ticker]
        if now < expiry:
            return cached_price
        del GLOBAL_PRICE_CACHE[ticker]
    price = Decimal(fetch_latest_stock_price(ticker))
    GLOBAL_PRICE_CACHE[ticker] = (price, now + CACHE_TIMEOUT)
    return price

# Constants
PUT_FUTURES_MULTIPLIERS = {'MES': -5, 'YM': -5, 'ES': -50, 'RTY': -50, 'MNQ': -2, 'NQ': -20, 'MYM': -0.5, 'SSO': -200, 'QLD': -200}
EQUITY_FUTURES_MULTIPLIERS = {'MES': 5, 'ES': 50, 'RTY': 50, 'MNQ': 2, 'NQ': 20, 'MYM': 0.5, 'YM': 5, 'SSO': 2, 'QLD': 2}
EQUITY_MULTIPLIERS = {'MES': 5, 'ES': 50, 'RTY': 50, 'MNQ': 2, 'NQ': 20, 'MYM': 0.5, 'YM': 5, 'SSO': 2, 'QLD': 2}
NET_LOSS_MULTIPLIERS = {'MES': 5, 'ES': 50, 'RTY': 50, 'MNQ': 2, 'NQ': 20, 'MYM': 0.5, 'YM': 5}
