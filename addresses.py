# Print all deposit addresses (static and dynamic)
from modules.bybit_client import print_all_deposit_addresses
print_all_deposit_addresses()

# To view static deposit addresses directly:
try:
	from static_deposit_addresses import STATIC_DEPOSIT_ADDRESSES
	print("\n[STATIC DEPOSIT ADDRESSES]")
	for chain, coins in STATIC_DEPOSIT_ADDRESSES.items():
		for coin, addr in coins.items():
			print(f"{coin} on {chain}: {addr}")
except Exception as e:
	print(f"[Static Address Error] {e}")