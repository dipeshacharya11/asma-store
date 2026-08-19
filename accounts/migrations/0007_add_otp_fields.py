# Generated migration to add fields to OTP model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_rename_accounts_ver_phone_number_7b8a9e_idx_accounts_ve_phone_n_88f0e9_idx_and_more'),
        ('store', '0001_initial'),  # Assuming store's initial migration is 0001_initial, adjust if needed
    ]

    operations = [
        migrations.AddField(
            model_name='otp',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='otp',
            name='session_key',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name='otp',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='otp',
            name='user_agent',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='otp',
            name='sparrow_message_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='otp',
            name='sparrow_response_code',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='otp',
            name='related_order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='otp_used', to='store.order'),
        ),
    ]