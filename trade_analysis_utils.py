from rest_framework import status
from .adminBaseService import AdminBaseService
from api.utils.messages.userMessages import *
from decimal import Decimal
from api.utils.stock_utils import fetch_latest_stock_price, fetch_stock_price_by_date, get_ticker_symbol, price_cache_expiry
from api.utils.messages.commonMessages import *
from api.models import Trade, Trade_History, ATHSubmission
from django.db.models import F, Sum, Min, Max
from api.utils.getUserByToken import get_user_by_token
from django.db.models.functions import Length
from api.serializers.user import *
from api.serializers.investorType import *
from api.serializers.trade.trade_serializer import TradeSerializer
from api.serializers.tradeHistory.tradeHistory_serializer import TradeHistorySerializer
from api.serializers.ATHSubmission.ATHSubmission_serializer import ATHSubmissionSerializer
from api.utils.customPagination import CustomPagination
from datetime import datetime, timedelta, date
import re
import logging
import calendar
from api.utils.global_data import dashboard_data
import json
import pandas as pd
import numpy as np
import os

NUMBER_AND_LETTER_PATTERN = re.compile(
    r'(\d{2}[A-Z]{3}\d{2}|\d{2}/\d{2}/\d{4}|\d{2}\d{2}\d{4})\s+(\d+\.*\d*)\s*([CP])'
)
STOCK_SYMBOL_PATTERN = re.compile(r"([A-Z&\s]+)")

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
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%m/%d/%Y")
        except ValueError:
            pass
    match = re.search(r'\b(\d{2}[A-Z]{3}\d{2})\b', stock_name)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%d%b%y")
        except ValueError:
            pass

    return None

def is_short_term(expiration_date, threshold_days=5):
    now = datetime.now()
    diff = (expiration_date - now).days
    return diff < threshold_days

def normalize_stock_symbol(symbol: str) -> str | None:
    symbol_clean = symbol.strip().lstrip('$').upper()
    return FUTURES_TICKER_MAPPING.get(symbol_clean, symbol_clean)

def get_multiplier(multiplier_dict: dict, stock_symbol: str):
    if stock_symbol in multiplier_dict:
        return multiplier_dict[stock_symbol]
    return next((multiplier for sym, multiplier in multiplier_dict.items() if sym in stock_symbol), None)

FUTURES_TICKER_MAPPING = {
    "ESH": "ESH25.CME", "ESM": "ESM25.CME", "ESU": "ESU25.CME", "ESZ": "ESZ25.CME", "MESH": "MESH25.CME", "MESM": "MESM25.CME", "MESU": "MESU25.CME", "MESZ": "MESZ25.CME",   
    "NQH": "NQH25.CME", "NQM": "NQM25.CME", "NQU": "NQU25.CME", "NQZ": "NQZ25.CME", "MNQH": "MNQH25.CME", "MNQM": "MNQM25.CME", "MNQU": "MNQU25.CME", "MNQZ": "MNQZ25.CME",   
    "YMH": "YMH25.CME", "YMM": "YMM25.CME",   "YMU": "YMU25.CME",   "YMZ": "YMZ25.CME", "MYMH": "MYMH25.CBT", "MYMM": "MYMM25.CBT", "MYMU": "MYMU25.CBT", "MYMZ": "MYMZ25.CBT",   
    "RTYH": "RTYH25.CME", "RTYM": "RTYM25.CME", "RTYU": "RTYU25.CME", "RTYZ": "RTYZ25.CME",   
}

def third_friday(year: int, month: int) -> datetime:
    month_cal = calendar.monthcalendar(year, month)
    if month_cal[0][calendar.FRIDAY]:
        day = month_cal[2][calendar.FRIDAY]
    else:
        day = month_cal[3][calendar.FRIDAY]
    return datetime(year, month, day)

def get_future_contract_ticker(raw_symbol: str, expiration_date: datetime) -> str:
    futures_prefixes = {"ES", "MES", "MYM", "YM", "NQ", "MNQ", "RTY"}
    symbol = raw_symbol.strip().lstrip('$').upper()
    
    if not any(symbol.startswith(prefix) for prefix in futures_prefixes):
        return get_ticker_symbol(symbol)
    
    if expiration_date.month not in (3, 6, 9, 12):
        return get_ticker_symbol(symbol)
    
    year = expiration_date.year
    if expiration_date.month == 3:
        cutoff = third_friday(year, 3)
        suffix = "M" if expiration_date > cutoff else "H"
    elif expiration_date.month == 6:
        cutoff = third_friday(year, 6)
        suffix = "U" if expiration_date > cutoff else "M"
    elif expiration_date.month == 9:
        cutoff = third_friday(year, 9)
        suffix = "Z" if expiration_date > cutoff else "U"
    elif expiration_date.month == 12:
        suffix = "Z"
    else:
        return get_ticker_symbol(symbol)
    
    key = f"{symbol}{suffix}"
    return FUTURES_TICKER_MAPPING.get(key, f"{key}25.CME")

PUT_FUTURES_MULTIPLIERS = {'MES': -5, 'YM': -5, 'ES': -50, 'RTY': -50, 'MNQ': -2, 'NQ': -20, 'MYM': -0.5, 'SSO': -200, 'QLD': -200}
EQUITY_FUTURES_MULTIPLIERS = {'MES': 5, 'ES': 50, 'RTY': 50, 'MNQ': 2, 'NQ': 20, 'MYM': 0.5, 'YM': 5, 'SSO': 2, 'QLD': 2}
EQUITY_MULTIPLIERS = {'MES': 5, 'ES': 50, 'RTY': 50, 'MNQ': 2, 'NQ': 20, 'MYM': 0.5, 'YM': 5, 'SSO': 2, 'QLD': 2}
NET_LOSS_MULTIPLIERS = {'MES': 5, 'ES': 50, 'RTY': 50, 'MNQ': 2,'NQ': 20, 'MYM': 0.5, 'YM': 5}

CACHE_TIMEOUT = timedelta(seconds=price_cache_expiry)
GLOBAL_PRICE_CACHE = {}

def get_price_cached(ticker: str) -> Decimal:
    now = datetime.now()
    if ticker in GLOBAL_PRICE_CACHE:
        cached_price, expiry_time = GLOBAL_PRICE_CACHE[ticker]
        if now < expiry_time:
            return cached_price
        del GLOBAL_PRICE_CACHE[ticker]
    price = Decimal(fetch_latest_stock_price(ticker))
    expiry_time = now + CACHE_TIMEOUT
    GLOBAL_PRICE_CACHE[ticker] = (price, expiry_time)
    return price

def handle_put_option(final_price, stock_symbol, quantity, stock_price, total_equity_value, total_options_value, total_futures_contracts_values):
    final_price_dec = Decimal(final_price)
    if (mult := get_multiplier(PUT_FUTURES_MULTIPLIERS, stock_symbol)) is not None:
        if final_price_dec > stock_price:
            total_equity_value += final_price_dec * Decimal(mult) * quantity
        else:
            total_futures_contracts_values += final_price_dec * Decimal(mult) * quantity
    else:
        if final_price_dec > stock_price:
            total_equity_value += final_price_dec * Decimal(-100) * quantity
        else:
            total_options_value += final_price_dec * Decimal(-100) * quantity

    return total_equity_value, total_options_value, total_futures_contracts_values

def handle_call_option(final_price, stock_symbol, quantity, stock_price, total_equity_value):
    final_price_dec = Decimal(final_price)
    if (mult := get_multiplier(PUT_FUTURES_MULTIPLIERS, stock_symbol)) is not None:
        total_equity_value -= final_price_dec * Decimal(mult) * quantity
    else:
        total_equity_value -= final_price_dec * Decimal(-100) * quantity
    return total_equity_value

def handle_neither_instrument(purchase_price, stock_symbol, quantity, stock_price, total_equity_value, daily_positions_value):
    purchase_dec = Decimal(purchase_price)
    if (mult := get_multiplier(EQUITY_FUTURES_MULTIPLIERS, stock_symbol)) is not None:
        total_equity_value += quantity * purchase_dec * Decimal(mult)
        daily_positions_value += quantity * stock_price * Decimal(mult)
    else:
        total_equity_value += quantity * purchase_dec
        daily_positions_value += quantity * stock_price
    return total_equity_value, daily_positions_value

def calculate_exposure(trades):
    total_equity_value = Decimal('0.0')
    total_options_value = Decimal('0.0')
    daily_positions_value = Decimal('0.0')
    total_futures_contracts_values = Decimal('0.0')
    current_account_value = Decimal('0.0')

    for t in trades:
        final_price, letter = extract_number_and_letter(t.stock_name)
        raw_symbol = extract_stock_symbol(t.stock_name)
        if raw_symbol:
            const_expiration = extract_expiration_date(t.stock_name)
            if const_expiration:
                ticker = get_future_contract_ticker(raw_symbol, const_expiration)
            else:
                ticker = get_ticker_symbol(raw_symbol)
        else:
            ticker = None

        underlying = raw_symbol if raw_symbol else ""
        quantity = Decimal(t.quantity)
        current_account_value += Decimal(t.market_value)

        stock_price = get_price_cached(ticker) if ticker else Decimal('0.0')

        if letter == 'P' and final_price:
            (total_equity_value,
             total_options_value,
             total_futures_contracts_values) = handle_put_option(
                 final_price, underlying, quantity, stock_price,
                 total_equity_value, total_options_value, total_futures_contracts_values
             )
        elif letter == 'C' and final_price:
            if Decimal(final_price) < stock_price:
                total_equity_value = handle_call_option(
                    final_price, underlying, quantity, stock_price,
                    total_equity_value
                )
        else:
            total_equity_value, daily_positions_value = handle_neither_instrument(
                t.price, underlying, quantity, stock_price,
                total_equity_value, daily_positions_value
            )
    total_exposure_value = total_equity_value + total_futures_contracts_values + total_options_value
    return {
        "total_equity_value": total_equity_value,
        "total_exposure_value": total_exposure_value,
        "daily_positions_value": round(daily_positions_value, 2),
        "current_account_value": current_account_value,
    }

def handle_put_in_down_move(final_price: Decimal, stock_symbol: str, quantity: Decimal,
                            adjusted_stock_price: Decimal, what_if_exposure: Decimal,
                            what_if_options_value: Decimal, net_loss: Decimal):
    if (mult := get_multiplier(PUT_FUTURES_MULTIPLIERS, stock_symbol)) is not None:
        what_if_exposure += final_price * Decimal(mult) * quantity
    else:
        what_if_options_value += final_price * Decimal(-100) * quantity
    net_loss_multiplier = NET_LOSS_MULTIPLIERS.get(stock_symbol, 100)
    net_loss += (final_price - adjusted_stock_price) * Decimal(net_loss_multiplier) * quantity
    return what_if_exposure, what_if_options_value, net_loss

def handle_call_in_up_move(final_price: Decimal, stock_symbol: str, quantity: Decimal,
                           adjusted_stock_price: Decimal, what_if_exposure: Decimal,
                           what_if_options_value: Decimal, net_loss: Decimal):
    futures_multipliers = {"MES": 5, "ES": 50, "RTY": 50, "MNQ": 2, "NQ": 20, "MYM": 0.5, "SSO": 200, "QLD": 200}
    if (mult := get_multiplier(futures_multipliers, stock_symbol)) is not None:
        what_if_exposure += final_price * Decimal(mult) * quantity
    else:
        what_if_options_value += final_price * Decimal(100) * quantity

    net_loss_multiplier = NET_LOSS_MULTIPLIERS.get(stock_symbol, 100)
    net_loss += (adjusted_stock_price - final_price) * Decimal(net_loss_multiplier) * quantity
    return what_if_exposure, what_if_options_value, net_loss

def handle_regular_instrument_in_what_if(letter: str, quantity: Decimal, purchase_price: Decimal,
                                         adjusted_change: Decimal, stock_symbol: str,
                                         what_if_equity_value: Decimal):
    if (mult := get_multiplier(EQUITY_MULTIPLIERS, stock_symbol)) is not None:
        what_if_equity_value += quantity * purchase_price * Decimal(mult) * adjusted_change
    else:
        what_if_equity_value += quantity * purchase_price * adjusted_change
    return what_if_equity_value

def calculate_what_if_exposure(trades, percent_change, is_increase):
   change = (Decimal(100) + percent_change) / Decimal(100) if is_increase else (Decimal(100) - percent_change) / Decimal(100)
   what_if_exposure = Decimal('0.0')
   what_if_options_value = Decimal('0.0')
   what_if_equity_value = Decimal('0.0')
   net_loss = Decimal('0.0')

   for t in trades:
       final_price, letter = extract_number_and_letter(t.stock_name)
       raw_symbol = extract_stock_symbol(t.stock_name)
       if raw_symbol:
           expiration_date = extract_expiration_date(t.stock_name)
           if expiration_date:
               ticker = get_future_contract_ticker(raw_symbol, expiration_date)
           else:
               ticker = get_ticker_symbol(raw_symbol)
       else:
           ticker = None

       underlying = raw_symbol if raw_symbol else ""
       quantity = Decimal(t.quantity)

       stock_price = get_price_cached(ticker) if ticker else Decimal('0.0')
       #if ticker:
           #print(f"Fetched price for {ticker}: {stock_price}")

       if ticker in ["SSO", "QLD"]:
           adjusted_change = (Decimal(100) + (2 * percent_change if is_increase else -2 * percent_change)) / Decimal(100)
       else:
           adjusted_change = change
       adjusted_stock_price = stock_price * adjusted_change

       if not is_increase and letter == "P" and final_price:
           if Decimal(final_price) > adjusted_stock_price:
               (what_if_exposure, what_if_options_value, net_loss) = handle_put_in_down_move(
                   Decimal(final_price), underlying, quantity, adjusted_stock_price,
                   what_if_exposure, what_if_options_value, net_loss
               )
       elif is_increase and letter == "C" and final_price:
           if Decimal(final_price) < adjusted_stock_price:
               (what_if_exposure, what_if_options_value, net_loss) = handle_call_in_up_move(
                   Decimal(final_price), underlying, quantity, adjusted_stock_price,
                   what_if_exposure, what_if_options_value, net_loss
               )
       elif letter not in ["C", "P"]:
           what_if_equity_value = handle_regular_instrument_in_what_if(
               letter, quantity, Decimal(t.price), adjusted_change, underlying, what_if_equity_value
           )
   total_what_if_exposure = what_if_exposure + what_if_equity_value + what_if_options_value + net_loss
   return {
       "total_what_if_exposure": total_what_if_exposure,
       "net_loss": net_loss,
   }

def handle_regular_instrument_in_down_equity(letter: str, quantity: Decimal, price: Decimal,
                                               market_value: Decimal, adjusted_change: Decimal,
                                               stock_symbol: str) -> Decimal:
    equity_multipliers = {'MES': 5, 'ES': 50, 'RTY': 50, 'MNQ': 2, 'NQ': 20, 'MYM': 0.5, 'YM': 5}
    if (mult := get_multiplier(equity_multipliers, stock_symbol)) is not None:
        return quantity * price * adjusted_change * Decimal(mult)
    return market_value * adjusted_change

def handle_option_in_down_equity(market_value: Decimal) -> Decimal:
    return market_value

def calculate_what_if_down_equity(trades, percentageDown):
    change = (Decimal(100) - percentageDown) / Decimal(100)
    what_if_down_equity = Decimal('0.0')

    for t in trades:
        final_price, letter = extract_number_and_letter(t.stock_name)
        raw_symbol = extract_stock_symbol(t.stock_name)
        
        if raw_symbol:
            expiration_date = extract_expiration_date(t.stock_name)
            if expiration_date:
                resolved_symbol = get_future_contract_ticker(raw_symbol, expiration_date)
            else:
                resolved_symbol = get_ticker_symbol(raw_symbol)
        else:
            resolved_symbol = None

        quantity = Decimal(t.quantity)

        if resolved_symbol in ["SSO", "QLD"]:
            adjusted_change = (Decimal(100) - 2 * percentageDown) / Decimal(100)
        elif "cash" in t.stock_name.lower():
            adjusted_change = Decimal(1)
        else:
            adjusted_change = change

        if letter in ["C", "P"]:
            what_if_down_equity += handle_option_in_down_equity(Decimal(t.market_value))
        else:
            portion = handle_regular_instrument_in_down_equity(
                letter, quantity, Decimal(t.price), Decimal(t.market_value), adjusted_change, resolved_symbol
            )
            what_if_down_equity += portion

    return what_if_down_equity

def calculate_downward_exposure_with_expiration(trades, percentageDown, expirationThreshold: int):
    short_term_contracts = 0
    short_term_exposure = Decimal('0.0')
    short_term_options_value = Decimal('0.0')
    short_term_net_loss = Decimal('0.0')

    long_term_contracts = 0
    long_term_exposure = Decimal('0.0')
    long_term_options_value = Decimal('0.0')
    long_term_net_loss = Decimal('0.0')

    change = (Decimal(100) - Decimal(percentageDown)) / Decimal(100)

    for t in trades:
        final_price_str, letter = extract_number_and_letter(t.stock_name)
        raw_symbol = extract_stock_symbol(t.stock_name)
        
        if raw_symbol:
            expiration_date = extract_expiration_date(t.stock_name)
            if expiration_date:
                ticker = get_future_contract_ticker(raw_symbol, expiration_date)
            else:
                ticker = get_ticker_symbol(raw_symbol)
        else:
            ticker = None

        stock_price = get_price_cached(ticker) if ticker else Decimal('0.0')

        if ticker in ["SSO", "QLD"]:
            adjusted_change = (Decimal(100) + (Decimal(-2) * Decimal(percentageDown))) / Decimal(100)
        else:
            adjusted_change = change

        adjusted_stock_price = stock_price * adjusted_change

        if letter != "P":
            continue
        
        expiration_date = extract_expiration_date(t.stock_name)
        if not expiration_date:
            continue

        is_short = is_short_term(expiration_date, threshold_days=expirationThreshold)
        try:
            final_price_dec = Decimal(final_price_str)
        except Exception:
            continue

        quantity = Decimal(t.quantity)

        if final_price_dec > adjusted_stock_price:
            if is_short:
                short_term_contracts += 1
                st_exposure, st_options_value, st_net_loss = handle_put_in_down_move(
                    final_price_dec, raw_symbol, quantity, adjusted_stock_price,
                    short_term_exposure, short_term_options_value, short_term_net_loss
                )
                short_term_exposure = st_exposure
                short_term_options_value = st_options_value
                short_term_net_loss = st_net_loss
            else:
                long_term_contracts += 1
                lt_exposure, lt_options_value, lt_net_loss = handle_put_in_down_move(
                    final_price_dec, raw_symbol, quantity, adjusted_stock_price,
                    long_term_exposure, long_term_options_value, long_term_net_loss
                )
                long_term_exposure = lt_exposure
                long_term_options_value = lt_options_value
                long_term_net_loss = lt_net_loss

    return {
        "short_term": {
            "short_term_contracts": short_term_contracts,
            "short_term_exposure": short_term_exposure + short_term_options_value + short_term_net_loss,
        },
        "long_term": {
            "long_term_contracts": long_term_contracts,
            "long_term_exposure": long_term_exposure + long_term_options_value + long_term_net_loss,
        }
    }

def calculate_portfolio_exposures(percentageUp, percentageDown, expirationThreshold):
    total_trades = Trade.objects.all()
    account_ids = total_trades.values_list('account_id', flat=True).distinct()
    portfolio_exposures = []

    for account_id in account_ids:
        trades = total_trades.filter(account_id=account_id)
        if not trades.exists():
            continue

        result = calculate_exposure(trades)
        total_exposure_value = result["total_exposure_value"]
        daily_positions_value = result["daily_positions_value"]
        total_equity_value = result["total_equity_value"]
        current_account_value = result["current_account_value"]

        down_result = calculate_what_if_exposure(trades, percentageDown, False)
        up_result = calculate_what_if_exposure(trades, percentageUp, True)

        what_if_down_exposure = down_result["total_what_if_exposure"]
        what_if_down_net_loss = down_result["net_loss"]
        what_if_up_exposure = up_result["total_what_if_exposure"]
        what_if_down_equity = calculate_what_if_down_equity(trades, percentageDown) + what_if_down_net_loss

        downward_put_exposure_result = calculate_downward_exposure_with_expiration(
            trades, percentageDown, expirationThreshold
        )
        short_term_puts_itm = downward_put_exposure_result["short_term"]["short_term_contracts"]
        short_term_puts_exposure = downward_put_exposure_result["short_term"]["short_term_exposure"]
        long_term_puts_itm = downward_put_exposure_result["long_term"]["long_term_contracts"]
        long_term_puts_exposure = downward_put_exposure_result["long_term"]["long_term_exposure"]

        what_if_down_leverage = (
            what_if_down_exposure / what_if_down_equity if what_if_down_equity != 0 else None
        )
        current_leverage = (
            total_equity_value / current_account_value if current_account_value != 0 else None
        )

        portfolio_exposures.append({
            "account_id": account_id,
            "total_exposure_value": total_exposure_value,
            "daily_positions_value": daily_positions_value,
            "total_equity_value": total_equity_value,
            "current_account_value": current_account_value,
            "what_if_down_exposure": what_if_down_exposure,
            "what_if_up_exposure": what_if_up_exposure,
            "current_leverage": current_leverage,
            "what_if_down_equity": what_if_down_equity,
            "what_if_down_leverage": what_if_down_leverage,
            "short_term_puts_itm": short_term_puts_itm,
            "short_term_puts_exposure": short_term_puts_exposure,
            "long_term_puts_itm": long_term_puts_itm,
            "long_term_puts_exposure": long_term_puts_exposure,
        })
    return portfolio_exposures

def safe_trade_dataframe(tradeHistory, required_fields=None):
    if required_fields is None:
        required_fields = []
    data = []
    for t in tradeHistory:
        d = t.__dict__
        if all(field in d and isinstance(d[field], str) for field in required_fields):
            data.append(d)
    return pd.DataFrame(data)

def process_standard_options(tradeHistory):
    logger.info("Starting process_standard_options for %d trades", len(tradeHistory))
    df = safe_trade_dataframe(tradeHistory, required_fields=["symbol", "code"])
    df = df[df['symbol'].apply(lambda x: isinstance(x, str))]
    df.loc[:, 'letter'] = df['symbol'].apply(lambda x: extract_number_and_letter(x)[1])
    df = df[df['letter'].isin(['C', 'P'])]
    df.loc[:, 'code_upper'] = df['code'].str.upper()
    contracts_sold = df[df['code_upper'] == 'O'].shape[0]
    
    expired_calls = df[(df['code_upper'] == 'C;EP') & (df['letter'] == 'C')].shape[0]
    expired_puts = df[(df['code_upper'] == 'C;EP') & (df['letter'] == 'P')].shape[0]
    
    expired_call_premiums = df[(df['code_upper'] == 'C;EP') & (df['letter'] == 'C')]['realized_profit_loss'].sum()
    expired_put_premiums = df[(df['code_upper'] == 'C;EP') & (df['letter'] == 'P')]['realized_profit_loss'].sum()
    
    open_positions = df[df['code_upper'] == 'O'].to_dict('records')
    closed_positions = df[df['code_upper'] == 'C'].to_dict('records')
    result = {
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "contracts_sold": contracts_sold,
        "expired_calls": expired_calls,
        "expired_call_premiums": expired_call_premiums,
        "expired_puts": expired_puts,
        "expired_put_premiums": expired_put_premiums
    }
    logger.info("Finished process_standard_options: %s", result)
    return result

def match_standard_options(closed_positions):
    logger.info("Starting vectorized_match_standard_options for %d closed trades", len(closed_positions))
    if not closed_positions:
        result = {
            "calls_bought_back": 0,
            "puts_bought_back": 0,
            "pnl_calls_bought_back": Decimal('0.0'),
            "pnl_puts_bought_back": Decimal('0.0')
        }
        logger.info("Finished vectorized_match_standard_options: %s", result)
        return result
    df = pd.DataFrame(closed_positions)
    df = df[df['code'].str.upper() != "C;EP"]
    logger.debug("After filtering out code 'C;EP': %d trades", len(df))
    df['option_letter'] = df['symbol'].apply(lambda s: extract_number_and_letter(s)[1])
    
    calls_df = df[df['option_letter'] == "C"]
    puts_df = df[df['option_letter'] == "P"]
    
    calls_bought_back = len(calls_df)
    pnl_calls_bought_back = calls_df['realized_profit_loss'].fillna(0).sum()
    puts_bought_back = len(puts_df)
    pnl_puts_bought_back = puts_df['realized_profit_loss'].fillna(0).sum()
    result = {
        "calls_bought_back": calls_bought_back,
        "puts_bought_back": puts_bought_back,
        "pnl_calls_bought_back": Decimal(str(pnl_calls_bought_back)),
        "pnl_puts_bought_back": Decimal(str(pnl_puts_bought_back))
    }
    logger.info("Finished vectorized_match_standard_options: %s", result)
    return result

def process_assigned_trades(tradeHistory):
    logger.info("Starting process_assigned_trades for %d trades", len(tradeHistory))

    df = safe_trade_dataframe(tradeHistory, required_fields=["symbol", "code"])

    df = df[df['symbol'].apply(lambda x: isinstance(x, str))]
    df.loc[:, 'letter'] = df['symbol'].apply(lambda x: extract_number_and_letter(x)[1])
    df = df[~df['letter'].isin(['C', 'P'])]
    df.loc[:, 'code_upper'] = df['code'].str.upper()
    
    assigned_closed_count = df[df['code_upper'] == 'A;C'].shape[0]
    assigned_closed_realized_pnl = df[df['code_upper'] == 'A;C']['realized_profit_loss'].sum()
    assigned_opened_count = df[df['code_upper'] == 'A;O'].shape[0]
    assigned_opened_mtm_pnl = df[df['code_upper'] == 'A;O']['mtm_profit_loss'].sum()
    
    result = {
        "assigned_closed_count": assigned_closed_count,
        "assigned_closed_realized_pnl": assigned_closed_realized_pnl,
        "assigned_opened_count": assigned_opened_count,
        "assigned_opened_mtm_pnl": assigned_opened_mtm_pnl
    }
    logger.info("Finished process_assigned_trades: %s", result)
    return result

def calculate_options_premiums(tradeHistory):
    logger.info("Starting calculate_options_premiums for %d trades", len(tradeHistory))
    std_options = process_standard_options(tradeHistory)
    matched_options = match_standard_options(std_options["closed_positions"])
    assigned = process_assigned_trades(tradeHistory)
    premiums = {
        "expired_calls": std_options["expired_calls"],
        "expired_call_premiums": std_options["expired_call_premiums"],
        "expired_puts": std_options["expired_puts"],
        "expired_put_premiums": std_options["expired_put_premiums"],
        "calls_bought_back": matched_options["calls_bought_back"],
        "pnl_calls_bought_back": matched_options["pnl_calls_bought_back"],
        "puts_bought_back": matched_options["puts_bought_back"],
        "pnl_puts_bought_back": matched_options["pnl_puts_bought_back"],
        "total_contracts_sold": std_options["contracts_sold"],
        "assigned_closed_count": assigned["assigned_closed_count"],
        "assigned_closed_realized_pnl": assigned["assigned_closed_realized_pnl"],
        "assigned_opened_count": assigned["assigned_opened_count"],
        "assigned_opened_mtm_pnl": assigned["assigned_opened_mtm_pnl"]
    }
    logger.info("Options premiums calculated: %s", premiums)
    return premiums

def calculate_portfolio_premiums():
    logger.info("Starting calculate_portfolio_premiums")
    total_trade_history = Trade_History.objects.all()
    account_ids = total_trade_history.values_list('account_id', flat=True).distinct()
    portfolio_premiums = []
    logger.info("Found %d unique account IDs", len(account_ids))

    for account_id in account_ids:
        trade_history = total_trade_history.filter(account_id=account_id)
        if not trade_history.exists():
            logger.debug("No trades for account_id: %s", account_id)
            continue

        dates = trade_history.aggregate(first_date=Min('date'), last_date=Max('date'))
        first_date = dates['first_date']
        last_date = dates['last_date']
        logger.debug("Account %s: first_date=%s, last_date=%s", account_id, first_date, last_date)

        premium = calculate_options_premiums(trade_history)
        
        account_data = {
            "account_id": account_id,
            "total_contracts_sold": premium["total_contracts_sold"],
            "expired_calls": premium["expired_calls"],
            "expired_call_premiums": premium["expired_call_premiums"],
            "expired_puts": premium["expired_puts"],
            "expired_put_premiums": premium["expired_put_premiums"],
            "calls_bought_back": premium["calls_bought_back"],
            "pnl_calls_bought_back": premium["pnl_calls_bought_back"],
            "puts_bought_back": premium["puts_bought_back"],
            "pnl_puts_bought_back": premium["pnl_puts_bought_back"],
            "assigned_closed_count": premium["assigned_closed_count"],
            "assigned_closed_realized_pnl": premium["assigned_closed_realized_pnl"],
            "assigned_opened_count": premium["assigned_opened_count"],
            "assigned_opened_mtm_pnl": premium["assigned_opened_mtm_pnl"],
            "expired_contracts_premiums": premium["expired_call_premiums"] + premium["expired_put_premiums"],
            "bought_back_contracts_pnl": premium["pnl_calls_bought_back"] + premium["pnl_puts_bought_back"],
            "assigned_contracts_pnl": premium["assigned_closed_realized_pnl"] + premium["assigned_opened_mtm_pnl"],
            "total_premiums": (
                premium["expired_call_premiums"] + premium["expired_put_premiums"] +
                premium["pnl_calls_bought_back"] + premium["pnl_puts_bought_back"] +
                premium["assigned_closed_realized_pnl"] + premium["assigned_opened_mtm_pnl"]
            ),
            "first_date": first_date,
            "last_date": last_date
        }
        portfolio_premiums.append(account_data)
        logger.debug("Processed account %s: %s", account_id, account_data)
    logger.info("Finished calculate_portfolio_premiums, processed %d accounts", len(portfolio_premiums))
    return portfolio_premiums

def calculate_all_portfolio_aths():
    results = {}
    submissions_qs = ATHSubmission.objects.all().values(
        'account_id', 'portfolioATHValue', 'portfolioATHDate', 'currentNAVValue'
    )
    sub_df = pd.DataFrame(list(submissions_qs))
    if sub_df.empty:
        return results

    for idx, row in sub_df.iterrows():
        account_id = row['account_id']
        submitted_value = Decimal(str(row['portfolioATHValue'])) if row['portfolioATHValue'] is not None else Decimal('0.0')
        ath_date = row['portfolioATHDate']
        currentNAVValue = Decimal(str(row['currentNAVValue'])) if row.get('currentNAVValue') is not None else Decimal('0.0')
        if isinstance(ath_date, (datetime, date)):
            ath_date_str = ath_date.strftime("%Y-%m-%d")
        else:
            ath_date_str = ath_date

        equity_values = Decimal('0.0')
        original_equity_values = Decimal('0.0')
        total_options_value = Decimal('0.0') 
        total_futures_values = Decimal('0.0')
        total_original_futures_values = Decimal('0.0')

        trades = Trade.objects.filter(account_id=account_id).values('stock_name', 'quantity', 'market_value', 'price')
        trades_df = pd.DataFrame(list(trades))
        if trades_df.empty:
            results[account_id] = {
                "new_ath_value": Decimal('0.0'),
                "ath_difference": -submitted_value,
                "total_options_value": total_options_value,
            }
            continue

        option_mask = trades_df['stock_name'].apply(lambda x: extract_number_and_letter(x)[1] in ["C", "P"])
        if not trades_df[option_mask].empty:
            options_sum = trades_df.loc[option_mask, 'market_value'].sum()
            total_options_value = Decimal(str(options_sum))

        trades_df = trades_df[~option_mask].copy()

        trades_df['stock_symbol'] = trades_df['stock_name'].apply(
            lambda x: normalize_stock_symbol(extract_stock_symbol(x)) if extract_stock_symbol(x) else None
        )
        trades_df = trades_df.dropna(subset=['stock_symbol']).copy()
        unique_symbols = trades_df['stock_symbol'].unique()
        price_dict = {}
        for sym in unique_symbols:
            price = fetch_stock_price_by_date(sym, ath_date_str)
            price_dict[sym] = price
            #print(f"Fetched ATH price for {sym} on {ath_date_str}: {price}")

        trades_df['stock_price'] = trades_df['stock_symbol'].map(price_dict)
        trades_df['multiplier'] = trades_df['stock_symbol'].apply(lambda x: get_multiplier(NET_LOSS_MULTIPLIERS, x))
        futures_df = trades_df[trades_df['multiplier'].notnull()].copy()
        equity_df = trades_df[trades_df['multiplier'].isnull()].copy()

        def calc_futures_value(row):
            mult = Decimal(str(row['multiplier']))
            qty = Decimal(str(row['quantity']))
            return row['stock_price'] * qty * mult

        def calc_original_futures_value(row):
            mult = Decimal(str(row['multiplier']))
            qty = Decimal(str(row['quantity']))
            trade_price = Decimal(str(row['price']))
            return qty * mult * trade_price

        if not futures_df.empty:
            futures_df['futures_values'] = futures_df.apply(calc_futures_value, axis=1)
            futures_df['original_futures_values'] = futures_df.apply(calc_original_futures_value, axis=1)
            total_futures_values = futures_df['futures_values'].sum()
            total_original_futures_values = futures_df['original_futures_values'].sum()
        else:
            total_futures_values = Decimal('0.0')
            total_original_futures_values = Decimal('0.0')

        if not equity_df.empty:
            equity_df['new_equity_value'] = equity_df.apply(
                lambda r: r['stock_price'] * Decimal(str(r['quantity'])), axis=1
            )
            equity_values = equity_df['new_equity_value'].sum()
            equity_df['original_equity_value'] = equity_df.apply(
                lambda r: Decimal(str(r['quantity'])) * Decimal(str(r['price'])), axis=1
            )
            original_equity_values = equity_df['original_equity_value'].sum()
        else:
            equity_values = Decimal('0.0')
            original_equity_values = Decimal('0.0')

        equity_diff = equity_values - original_equity_values
        net_difference = total_futures_values - total_original_futures_values

        new_ath_value = currentNAVValue + equity_diff + net_difference
        ath_difference = new_ath_value - submitted_value
        results[account_id] = {
            "new_ath_value": new_ath_value,
            "ath_difference": ath_difference,
            "total_options_value": total_options_value,
        }
    return results
