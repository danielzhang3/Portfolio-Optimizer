from rest_framework import serializers
from api.models import Trade_History

class TradeHistorySerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Trade_History
        fields = ['id', 'symbol', 'date', 'quantity', 't_price', 'c_price', 'proceeds', 'commissions', 'basis', 'realized_profit_loss', 'mtm_profit_loss', 'code', 'account_id']
