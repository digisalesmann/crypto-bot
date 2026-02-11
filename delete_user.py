from database import User

phone = "+2349136461787"
user = User.get_or_none(User.phone == phone)
if user:
    user.delete_instance(recursive=True)
    print(f"User {phone} deleted.")
else:
    print(f"User {phone} not found.")
