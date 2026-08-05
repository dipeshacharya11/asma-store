# Generated migration for VerifiedGuestPhone model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_remove_otp_accounts_ot_phone_n_2f5907_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='VerifiedGuestPhone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(help_text='Phone number in format: 97XXXXXXXX or 98XXXXXXXX', max_length=15, unique=True, validators=[django.core.validators.RegexValidator(message='Phone number must be 10 digits starting with 97 or 98', regex=r'^(97|98)\d{8}$')])),
                ('verified_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(help_text='When this verification expires and requires re-verification')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this verification is currently valid')),
                ('converted_to_user', models.ForeignKey(blank=True, help_text='If this phone was used to create an account, link to that user', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_guest_phone', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Verified Guest Phone',
                'verbose_name_plural': 'Verified Guest Phones',
            },
        ),
        migrations.AddIndex(
            model_name='verifiedguestphone',
            index=models.Index(fields=['phone_number'], name='accounts_ver_phone_number_7b8a9e_idx'),
        ),
        migrations.AddIndex(
            model_name='verifiedguestphone',
            index=models.Index(fields=['expires_at'], name='accounts_ver_expires_at_5f3d2a_idx'),
        ),
        migrations.AddIndex(
            model_name='verifiedguestphone',
            index=models.Index(fields=['is_active'], name='accounts_ver_is_active_d2e1b4_idx'),
        ),
    ]