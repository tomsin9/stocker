# Generated manually: Cleanup old data and make user field required

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def cleanup_old_data(apps, schema_editor):
    """
    清理舊數據：刪除所有沒有 user 的 Transaction 和 CashFlow
    因為無法確定這些數據屬於哪個用戶，所以刪除它們
    """
    Transaction = apps.get_model('portfolio', 'Transaction')
    CashFlow = apps.get_model('portfolio', 'CashFlow')
    
    # 刪除所有沒有 user 的記錄
    Transaction.objects.filter(user__isnull=True).delete()
    CashFlow.objects.filter(user__isnull=True).delete()


def reverse_cleanup(apps, schema_editor):
    """
    反向操作：無法恢復已刪除的數據
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portfolio', '0003_add_user_to_transaction_cashflow'),
    ]

    operations = [
        # 清理舊數據
        migrations.RunPython(
            code=cleanup_old_data,
            reverse_code=reverse_cleanup,
        ),
        # 將 user 字段設為必填（移除 null=True, blank=True）
        migrations.AlterField(
            model_name='transaction',
            name='user',
            field=models.ForeignKey(
                help_text='擁有此交易的用戶',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name='cashflow',
            name='user',
            field=models.ForeignKey(
                help_text='擁有此現金流的用戶',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cashflows',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        # 添加索引以提升查詢性能
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'date'], name='portfolio_t_user_id_date_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'asset'], name='portfolio_t_user_id_asset_idx'),
        ),
        migrations.AddIndex(
            model_name='cashflow',
            index=models.Index(fields=['user', 'date'], name='portfolio_c_user_id_date_idx'),
        ),
    ]
