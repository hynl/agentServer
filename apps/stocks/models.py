from django.db import models
from django.utils import timezone


# Create your models here.
class Stock(models.Model):
    ticker_symbol = models.CharField(max_length=20, db_index=True, verbose_name="股票代码")
    exchange = models.CharField(max_length=50, db_index=True, verbose_name="交易所")
    company_name = models.CharField(max_length=100, verbose_name="公司名称")
    isin = models.CharField(max_length=12, unique=True, blank=True, null=True, verbose_name="国际证券识别码")
    sector = models.CharField(max_length=50, db_index=True, blank=True, null=True, verbose_name="行业")
    industry = models.CharField(max_length=50, db_index=True, blank=True, null=True, verbose_name="子行业")
    logo_url = models.URLField(max_length=512, blank=True, null=True, verbose_name="公司logo")
    description = models.TextField(blank=True, null=True, verbose_name="公司简介")
    country = models.CharField(max_length=50, blank=True, null=True, verbose_name="国家")
    currency = models.CharField(max_length=10, blank=True, null=True, verbose_name="货币")
    last_updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    def __str__(self):
        return self.ticker_symbol + " - "+ self.company_name

    class Meta:
        verbose_name  = "股票"
        verbose_name_plural = "股票集"
        unique_together = ('ticker_symbol', 'exchange')
        ordering = ['ticker_symbol']
        indexes = [
            models.Index(fields=['ticker_symbol', 'exchange'], name='ticker_symbol_exchange_idx'),
        ]

