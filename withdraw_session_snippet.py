# --- Withdraw Session ---
_withdraw_sessions = {}

def get_withdraw_session(user_phone):
	return _withdraw_sessions.get(user_phone)

def set_withdraw_session(user_phone, session):
	_withdraw_sessions[user_phone] = session

def clear_withdraw_session(user_phone):
	if user_phone in _withdraw_sessions:
		del _withdraw_sessions[user_phone]
