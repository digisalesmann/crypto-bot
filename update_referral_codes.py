from database import User
import random, string

count = 0
for user in User.select():
    # Update if code is missing or not in new format
    if not user.referral_code or not user.referral_code.startswith('PPAY-'):
        letters = ''.join(random.choices(string.ascii_uppercase, k=4))
        digits = ''.join(random.choices(string.digits, k=4))
        user.referral_code = f"PPAY-{letters}-{digits}"
        user.save()
        count += 1
print(f"Updated referral codes for {count} users.")
