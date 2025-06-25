from django.db import models

class ATHSubmission(models.Model):
    id = models.AutoField(primary_key=True)
    account_id = models.IntegerField(blank=True, null=True)
    portfolioATHValue = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    portfolioATHDate = models.DateField(blank=True, null=True)
    currentNAVValue = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Account {self.account_id} - ATH: {self.portfolioATHValue} on {self.portfolioATHDate}"

    class Meta:
        db_table = 'ath_submissions'
        indexes = [
            models.Index(fields=['id', 'account_id', 'portfolioATHValue', 'portfolioATHDate', 'currentNAVValue']),
        ]
