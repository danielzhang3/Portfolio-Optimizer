import csv
from decimal import Decimal
from typing import List, Dict, Any
from django.db import transaction
from api.models import Trade

def parse_ibkr_trades(filename: str) -> List[Dict[str, Any]]:
    parsed_trades = []

    with open(filename, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header_found = False
        for row in reader:
            if not row:
                continue

            if row[0] == 'Open Positions' and row[1] == 'Header' and row[2] == 'DataDiscriminator':
                header_found = True
                continue

            if header_found and row[0] == 'Open Positions' and row[1] == 'Data' and row[2] == 'Summary':
                try:
                    symbol = row[5].strip()
                    quantity = int(float(row[6].strip()))
                    price = Decimal(row[10].strip().replace(',', '')) if row[10].strip() else Decimal('0')  
                    market_value = Decimal(row[11].strip().replace(',', '')) if row[11].strip() else Decimal('0')
                    cost_basis = Decimal(row[9].strip().replace(',', '')) if row[9].strip() else Decimal('0')
                    gain_loss = Decimal(row[13].strip().replace(',', '')) if row[13].strip() else Decimal('0')

                    trade_dict = {
                        'stock_name': symbol,
                        'quantity': quantity,
                        'price': price,
                        'market_value': market_value,
                        'cost_basis': cost_basis,
                        'gain_loss': gain_loss
                    }
                    parsed_trades.append(trade_dict)
                except Exception as e:
                    print(f"Skipping row due to error: {e}")
                    continue

    return parsed_trades

def parse_schwab_trades(filename: str) -> List[Dict[str, Any]]:
    parsed_trades = []

    with open(filename, newline='', encoding='utf-8-sig') as f:
        lines = f.readlines()

    header_index = None
    for idx, line in enumerate(lines):
        if line.startswith('"Symbol"'):
            header_index = idx
            break

    if header_index is None:
        print("No header row found in the Schwab file.")
        return []

    reader = csv.reader(lines[header_index:])
    next(reader) 

    for row in reader:
        try:
            if len(row) < 11:
                continue  

            symbol = row[0].strip()
            if not symbol:
                continue

            if "Cash & Cash Investments" in symbol:
                market_value = Decimal(row[6].replace(',', '').replace('$', '')) if row[6].strip() else Decimal('0')
                trade_dict = {
                    'stock_name': "Cash & Cash Investments",
                    'quantity': Decimal('0'), 
                    'price': Decimal('0'),  
                    'market_value': market_value,
                    'cost_basis': Decimal('0'),
                    'gain_loss': Decimal('0')
                }
                parsed_trades.append(trade_dict)
                continue

            quantity = int(float(row[2].replace(',', '')))
            price = Decimal(row[3].replace(',', '').replace('$', ''))
            market_value = Decimal(row[6].replace(',', '').replace('$', ''))
            cost_basis = Decimal(row[9].replace(',', '').replace('$', ''))
            gain_loss = Decimal(row[10].replace(',', '').replace('$', ''))

            trade_dict = {
                'stock_name': symbol,
                'quantity': quantity,
                'price': price,
                'market_value': market_value,
                'cost_basis': cost_basis,
                'gain_loss': gain_loss
            }
            parsed_trades.append(trade_dict)
        except Exception as e:
            print(f"Skipping row due to error: {e}")
            continue

    return parsed_trades

def import_trades_from_csv(filename: str, account_id: int, csv_type: str) -> Dict[str, Any]:
    try:
        if csv_type.lower() == 'ibkr':
            trades = parse_ibkr_trades(filename)
        elif csv_type.lower() == 'schwab':
            trades = parse_schwab_trades(filename)
        else:
            return {
                'success': False,
                'message': 'Invalid CSV type specified.',
                'total_trades': 0,
                'errors': ['Unsupported CSV type']
            }

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
                    Trade.objects.create(**trade_data)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Error importing trade {trade_data.get('stock_name', 'Unknown')}: {str(e)}")

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
