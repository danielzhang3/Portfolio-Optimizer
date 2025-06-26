from rest_framework import serializers
from api.models import Trade

class TradeSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Trade
        fields = ['stock_name', 'quantity', 'price', 'market_value', 'cost_basis', 'gain_loss', 'account_id']
