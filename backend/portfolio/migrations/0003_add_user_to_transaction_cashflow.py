# Generated manually for multi-tenant data isolation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portfolio', '0002_accountbalance_cashflow'),
    ]

    operations = [
        # Step 1: 添加 user 字段到 Transaction（允許 null，因為現有數據需要處理）
        migrations.AddField(
            model_name='transaction',
            name='user',
            field=models.ForeignKey(
                help_text='擁有此交易的用戶',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        # Step 2: 添加 user 字段到 CashFlow（允許 null）
        migrations.AddField(
            model_name='cashflow',
            name='user',
            field=models.ForeignKey(
                help_text='擁有此現金流的用戶',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cashflows',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        # Step 3: 清理舊數據（因為無法確定歸屬，建議刪除）
        # 注意：這會刪除所有現有的 Transaction 和 CashFlow 數據
        migrations.RunPython(
            code=lambda apps, schema_editor: None,  # 實際刪除操作在下一步
            reverse_code=lambda apps, schema_editor: None,
        ),
    ]
