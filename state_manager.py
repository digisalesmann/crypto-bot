# Simple in-memory session state for redeem and deposit flows
_redeem_sessions = {}
_deposit_sessions = {}

# --- Redeem Session ---
def get_redeem_session(user_phone):
	return _redeem_sessions.get(user_phone)

def set_redeem_session(user_phone, session):
	_redeem_sessions[user_phone] = session

def clear_redeem_session(user_phone):
	if user_phone in _redeem_sessions:
		del _redeem_sessions[user_phone]

# --- Swap Session ---
_swap_sessions = {}

def get_swap_session(user_phone):
	return _swap_sessions.get(user_phone)

def set_swap_session(user_phone, session):
	_swap_sessions[user_phone] = session

def clear_swap_session(user_phone):
	if user_phone in _swap_sessions:
		del _swap_sessions[user_phone]

# --- Deposit Session ---
def get_deposit_session(user_phone):
	return _deposit_sessions.get(user_phone)

def set_deposit_session(user_phone, session):
	_deposit_sessions[user_phone] = session

def clear_deposit_session(user_phone):
	if user_phone in _deposit_sessions:
		del _deposit_sessions[user_phone]

# --- Withdraw Session ---
_withdraw_sessions = {}

def get_withdraw_session(user_phone):
	return _withdraw_sessions.get(user_phone)

def set_withdraw_session(user_phone, session):
	_withdraw_sessions[user_phone] = session

def clear_withdraw_session(user_phone):
	if user_phone in _withdraw_sessions:
		del _withdraw_sessions[user_phone]
