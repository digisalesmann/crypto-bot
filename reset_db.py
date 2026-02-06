from database import db, User, Wallet, Transaction, Alert, SupportTicket

def reset():
    print("🔥 Resetting Database...")
    try:
        db.connect()
    except:
        pass # Already connected

    # 1. Drop old tables (Delete old structure)
    print("🗑️ Dropping old tables...")
    db.drop_tables([User, Wallet, Transaction, Alert, SupportTicket], safe=True)

    # 2. Create new tables (Apply new structure)
    print("✨ Creating new tables...")
    db.create_tables([User, Wallet, Transaction, Alert, SupportTicket], safe=True)
    
    print("✅ Database Reset Complete! You are ready.")
    db.close()

if __name__ == "__main__":
    reset()