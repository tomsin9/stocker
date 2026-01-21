# backend/portfolio/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from .models import Transaction, CashFlow

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def update_balance_on_transaction_save(sender, instance, created, **kwargs):
    """
    當交易被創建或更新時，更新用戶的現金餘額 cache
    """
    try:
        from .services import update_account_balance_cache
        update_account_balance_cache(instance.user)
    except Exception as e:
        # 記錄錯誤但不影響主業務流程
        logger.error(f"Failed to update balance cache after transaction save: {e}", exc_info=True)


@receiver(post_delete, sender=Transaction)
def update_balance_on_transaction_delete(sender, instance, **kwargs):
    """
    當交易被刪除時，重新計算用戶的現金餘額 cache
    """
    try:
        from .services import update_account_balance_cache
        update_account_balance_cache(instance.user)
    except Exception as e:
        logger.error(f"Failed to update balance cache after transaction delete: {e}", exc_info=True)


@receiver(post_save, sender=CashFlow)
def update_balance_on_cashflow_save(sender, instance, created, **kwargs):
    """
    當現金流被創建或更新時，更新用戶的現金餘額 cache
    """
    try:
        from .services import update_account_balance_cache
        update_account_balance_cache(instance.user)
    except Exception as e:
        logger.error(f"Failed to update balance cache after cashflow save: {e}", exc_info=True)


@receiver(post_delete, sender=CashFlow)
def update_balance_on_cashflow_delete(sender, instance, **kwargs):
    """
    當現金流被刪除時，重新計算用戶的現金餘額 cache
    """
    try:
        from .services import update_account_balance_cache
        update_account_balance_cache(instance.user)
    except Exception as e:
        logger.error(f"Failed to update balance cache after cashflow delete: {e}", exc_info=True)
