from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    name = 'portfolio'
    
    def ready(self):
        """
        當 Django 應用程序準備就緒時，導入 signals 模塊
        這樣可以確保 signals 被註冊
        """
        import portfolio.signals  # noqa
