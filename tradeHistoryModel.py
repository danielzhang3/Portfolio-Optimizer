from django.db import models
from django.utils import timezone
import datetime

class Trade_History(models.Model):
    id = models.AutoField(primary_key=True)
    symbol = models.CharField(max_length=100, blank=True, null=True)
    date = models.DateField(null=True)  # Use DateTimeField for date with time
    quantity = models.IntegerField(blank=True, null=True)
    t_price = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    c_price = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    proceeds = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    commissions = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    basis = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    realized_profit_loss = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    mtm_profit_loss = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    code = models.CharField(max_length=100, blank=True, null=True)
    account_id = models.IntegerField(blank = True, null = True)
    
    def __str__(self):
        return self.symbol
    
    class Meta:
        db_table = 'trade_history'
        indexes = [
            models.Index(fields=['id', 'symbol', 'date', 'quantity', 't_price', 'c_price', 'proceeds', 'commissions', 'basis', 'realized_profit_loss', 'mtm_profit_loss', 'code', 'account_id'])
        ]
