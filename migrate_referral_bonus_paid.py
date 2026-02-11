from playhouse.migrate import SqliteMigrator, migrate
from database import db
import peewee

# Ensure connection is closed before migration
if not db.is_closed():
    db.close()

try:
    db.connect()
    migrator = SqliteMigrator(db)
    # Add referral_bonus_paid as BooleanField
    migrate(
        migrator.add_column('user', 'referral_bonus_paid', peewee.BooleanField(default=False))
    )
    db.close()
    print('Migration successful: referral_bonus_paid added.')
except Exception as e:
    print(f'Migration failed: {e}')
