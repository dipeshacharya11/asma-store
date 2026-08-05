# Migration file to update OTP model to include purpose field and make user nullable
# We'll create it manually

# This is a placeholder; in a real environment, we would run `python manage.py makemigrations`
# But for the purpose of this task, we'll write the migration file.

# We'll assume the app is 'accounts' and the previous migration is 0002_auto_XXXXXXX.py
# We'll create 0003_alter_otp_purpose_user_nullable.py

# However, note that we are changing the model significantly:
# - Adding purpose field with default 'signup'
# - Making user field nullable and blank
# - We are also changing the way OTP is hashed (to support Argon2/PBKDF2) but that doesn't require a migration
# - We are also changing the max_attempts field to have a default (it already had a default)

# Let's write the migration.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_rename_accounts_otp_phone_idx_accounts_ot_phone_n_2f5907_idx_and_more'),
    ]

    operations = [
        # Add purpose field
        migrations.AddField(
            model_name='otp',
            name='purpose',
            field=models.CharField(choices=[('signup', 'Sign Up'), ('login', 'Login'), ('guest_checkout', 'Guest Checkout'), ('password_reset', 'Password Reset'), ('change_phone', 'Change Phone')], default='signup', max_length=20),
        ),
        # Alter user field to be nullable and blank
        migrations.AlterField(
            model_name='otp',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='otp_records', to=settings.AUTH_USER_MODEL),
        ),
    ]