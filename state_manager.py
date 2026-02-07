# state_manager.py
_sessions = {}

def get_session(user_phone, flow_type):
    return _sessions.get(f"{user_phone}_{flow_type}")

def set_session(user_phone, flow_type, data):
    _sessions[f"{user_phone}_{flow_type}"] = data

def clear_session(user_phone, flow_type):
    _sessions.pop(f"{user_phone}_{flow_type}", None)

def clear_all_sessions(user_phone):
    global _sessions
    _sessions = {k: v for k, v in _sessions.items() if not k.startswith(f"{user_phone}_")}