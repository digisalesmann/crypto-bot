from playhouse.migrate import SqliteMigrator, migrate
from database import db, User
import peewee

# Ensure connection is closed before migration
if not db.is_closed():
    db.close()

try:
    db.connect()
    migrator = SqliteMigrator(db)
    # Add referred_by_id as IntegerField (foreign key columns are integer)
    migrate(
        migrator.add_column('user', 'referred_by_id', peewee.IntegerField(null=True))
    )
    db.close()
    print('Migration successful: referred_by_id added.')
except Exception as e:
    print(f'Migration failed: {e}')
