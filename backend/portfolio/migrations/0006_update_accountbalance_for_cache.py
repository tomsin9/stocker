# Generated manually for AccountBalance cache implementation

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portfolio', '0005_rename_portfolio_c_user_id_date_idx_portfolio_c_user_id_aeab06_idx_and_more'),
    ]

    operations = [
        # Step 1: 添加 user 外鍵（允許 null，因為現有數據需要處理）
        migrations.AddField(
            model_name='accountbalance',
            name='user',
            field=models.ForeignKey(
                help_text='擁有此餘額的用戶',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='account_balance',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        # Step 2: 添加多幣種字段
        migrations.AddField(
            model_name='accountbalance',
            name='cash_usd',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='USD 現金餘額', max_digits=15),
        ),
        migrations.AddField(
            model_name='accountbalance',
            name='cash_hkd',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='HKD 現金餘額', max_digits=15),
        ),
        migrations.AddField(
            model_name='accountbalance',
            name='total_in_base',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='以基準幣種（USD）計算的總額', max_digits=15),
        ),
        # Step 3: 更新 verbose_name_plural
        migrations.AlterModelOptions(
            name='accountbalance',
            options={
                'verbose_name': 'Account Balance',
                'verbose_name_plural': 'Account Balances',
            },
        ),
        # Step 4: 刪除舊的 AccountBalance 記錄（因為沒有 user 關聯，無法確定歸屬）
        # 注意：這會刪除所有現有的 AccountBalance 數據
        migrations.RunPython(
            code=lambda apps, schema_editor: apps.get_model('portfolio', 'AccountBalance').objects.all().delete(),
            reverse_code=lambda apps, schema_editor: None,
        ),
        # Step 5: 將 user 字段設為必填（移除 null=True, blank=True）並添加唯一約束
        migrations.AlterField(
            model_name='accountbalance',
            name='user',
            field=models.ForeignKey(
                help_text='擁有此餘額的用戶',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='account_balance',
                to=settings.AUTH_USER_MODEL,
                unique=True
            ),
        ),
    ]
