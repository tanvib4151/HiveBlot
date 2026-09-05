from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared limiter instance so main.py and both routers reference the
# same rate-limit state instead of each creating their own.
limiter = Limiter(key_func=get_remote_address)
