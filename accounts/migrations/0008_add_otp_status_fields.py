# Generated migration to add status fields to OTP model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_otp_fields'),
        ('store', '0001_initial'),  # Adjust if store's initial migration is different
    ]

    operations = [
        migrations.AddField(
            model_name='otp',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('VERIFIED', 'Verified'), ('ALREADY_VERIFIED', 'Already Verified'), ('INVALID', 'Invalid'), ('EXPIRED', 'Expired'), ('MAX_ATTEMPTS', 'Max Attempts'), ('RESEND_COOLDOWN', 'Resend Cooldown'), ('RESEND_LIMIT', 'Resend Limit'), ('SEND_FAILED', 'Send Failed'), ('CONSUMED', 'Consumed')], default='PENDING', max_length=20),
        ),
        migrations.AddField(
            model_name='otp',
            name='resend_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='otp',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='otp_record', to='store.order'),
        ),
    ]