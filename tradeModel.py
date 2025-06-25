from django.db import models


class Trade(models.Model):
    id = models.AutoField(primary_key=True)
    stock_name = models.CharField(max_length=100, blank = True, null = True)
    quantity = models.IntegerField(blank = True, null = True)
    price = models.DecimalField(blank = True, null = True, max_digits=10, decimal_places=2)
    market_value = models.DecimalField(blank = True, null = True, max_digits=10, decimal_places=2)
    cost_basis = models.DecimalField(blank = True, null = True, max_digits=10, decimal_places=2)
    gain_loss = models.DecimalField(blank = True, null = True, max_digits=10, decimal_places=2)
    account_id = models.IntegerField(blank = True, null = True)

    def __str__(self):
        return self.stock_name

    class Meta:
        db_table = 'trades'
        indexes = [
            models.Index(fields=['id', 'stock_name', 'quantity', 'price', 'market_value', 'cost_basis', 'account_id'])
        ]

