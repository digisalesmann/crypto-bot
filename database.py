from peewee import *
import datetime
import os

# Connect to the file
db = SqliteDatabase('cex_ledger.db')
db.execute_sql('PRAGMA journal_mode=WAL;') # Keep WAL mode for speed

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    phone = CharField(unique=True)
    name = CharField(default="New Trader")
    onboarding_status = CharField(default='new') 
    language = CharField(default='en')
    referral_code = CharField(null=True)
    kyc_level = IntegerField(default=1)
    is_frozen = BooleanField(default=False) # For account freeze
    is_2fa_active = BooleanField(default=False) # For 2FA status
    created_at = DateTimeField(default=datetime.datetime.now)

class Wallet(BaseModel):
    user = ForeignKeyField(User, backref='wallets')
    currency = CharField()
    balance = FloatField(default=0.0)
    locked = FloatField(default=0.0)

class Transaction(BaseModel):
    user = ForeignKeyField(User, backref='transactions')
    type = CharField()
    currency = CharField()
    amount = FloatField()
    status = CharField(default='pending')
    tx_hash = CharField(null=True)
    timestamp = DateTimeField(default=datetime.datetime.now)

class Alert(BaseModel):
    user = ForeignKeyField(User, backref='alerts')
    symbol = CharField()
    target_price = FloatField()
    condition = CharField()
    is_active = BooleanField(default=True)

class SupportTicket(BaseModel):
    user = ForeignKeyField(User, backref='tickets')
    category = CharField() # 'general', 'security', 'billing'
    message = TextField()
    status = CharField(default='open') # open, closed, replied
    admin_reply = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    db.connect()
    db.execute_sql('PRAGMA journal_mode=WAL;')
    # Add SupportTicket to the tables list
    db.create_tables([User, Wallet, Transaction, Alert, SupportTicket], safe=True)
    db.close()