from django.db import models

from agentrtw import settings
from apps.stocks.models import Stock


# Create your models here.
class Watchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist', verbose_name="用户")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='watchlist', verbose_name="股票")
    interest_level = models.IntegerField(default=0, null=True, verbose_name="关注级别")
    position_shares = models.DecimalField(max_digits=18, decimal_places=4, default=0, null=True, verbose_name="持仓股数")
    average_cost_price = models.DecimalField(max_digits=18, decimal_places=4, default=0, null=True, verbose_name="持仓均价")
    notes = models.TextField(null=True, blank=True, verbose_name="备注")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")
    alert_settings = models.JSONField(null=True, blank=True, default=dict, verbose_name="预警设置", help_text='{"price": "alert"}')

    def __str__(self):
        return f"{self.user.username} - {self.stock.ticker_symbol}"
    class Meta:
        verbose_name = "自选股票"
        verbose_name_plural = "股票关注列表"
        ordering = ['-added_at']
        unique_together = ('user', 'stock')