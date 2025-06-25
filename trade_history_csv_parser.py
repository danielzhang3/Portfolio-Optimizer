import csv
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from django.db import transaction
from api.models import Trade_History

def parse_raw_ibkr(filename: str) -> List[Dict[str, Any]]:
    """
    Parses raw IBKR CSV file with correct column alignment.
    """
    parsed_orders = []

    with open(filename, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header_found = False
        for row in reader:
            if not row:
                continue

            # Detect header
            if row[0] == 'Trades' and row[1] == 'Header' and row[2] == 'DataDiscriminator':
                header_found = True
                continue

            if header_found and row[0] == 'Trades' and row[1] == 'Data' and row[2] == 'Order':
                try:
                    # Skip first 6 columns (Asset Category, Currency, Symbol, etc.)
                    symbol = row[5].strip()
                    date_str = row[6].split(',')[0].strip()
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    quantity = int(float(row[7].strip()))
                    t_price = Decimal(row[8].strip().replace(',', '')) if row[8].strip() else Decimal('0')
                    c_price = Decimal(row[9].strip().replace(',', '')) if row[9].strip() else Decimal('0')
                    proceeds = Decimal(row[10].strip().replace(',', '')) if row[10].strip() else Decimal('0')
                    commissions = Decimal(row[11].strip().replace(',', '')) if row[11].strip() else Decimal('0')
                    basis = Decimal(row[12].strip().replace(',', '')) if row[12].strip() else Decimal('0')
                    realized_pl = Decimal(row[13].strip().replace(',', '')) if row[13].strip() else Decimal('0')
                    mtm_pl = Decimal(row[14].strip().replace(',', '')) if row[14].strip() else Decimal('0')
                    code = row[15].strip() if len(row) > 15 else ''

                    trade_dict = {
                        'symbol': symbol,
                        'date': date,
                        'quantity': quantity,
                        't_price': t_price,
                        'c_price': c_price,
                        'proceeds': proceeds,
                        'commissions': commissions,
                        'basis': basis,
                        'realized_profit_loss': realized_pl,
                        'mtm_profit_loss': mtm_pl,
                        'code': code
                    }
                    parsed_orders.append(trade_dict)
                except Exception as e:
                    print(f"Skipping row due to error: {e}")
                    continue

    return parsed_orders

def import_trades_from_csv(filename: str, account_id: int) -> Dict[str, Any]:
    """
    Import trades from a raw IBKR CSV file into the Trade_History model.
    """
    try:
        trades = parse_raw_ibkr(filename)
        
        if not trades:
            return {
                'success': False,
                'message': 'No valid trades found in the CSV file.',
                'total_trades': 0,
                'errors': []
            }
        
        with transaction.atomic():
            imported_count = 0
            errors = []

            for trade_data in trades:
                try:
                    trade_data['account_id'] = account_id
                    Trade_History.objects.create(**trade_data)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Error importing trade {trade_data.get('symbol', 'Unknown')}: {str(e)}")

            if errors and imported_count == 0:
                raise Exception("No trades were imported successfully.")

            return {
                'success': True,
                'message': f"Successfully imported {imported_count} trades" +
                           (f" with {len(errors)} errors." if errors else "."),
                'total_trades': imported_count,
                'errors': errors
            }

    except Exception as e:
        return {
            'success': False,
            'message': f"Failed to import trades: {str(e)}",
            'total_trades': 0,
            'errors': [str(e)]
        }
