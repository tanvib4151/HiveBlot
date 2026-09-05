"""
Dummy env vars for the whole test suite.

config.Settings is instantiated at import time (deliberately - see config.py),
so these have to be set before anything under app/ is imported. Putting this
at api/ root also puts api/ on sys.path, so `from app...` resolves in tests.

These are fake values: nothing in the test suite talks to Supabase, OpenAI, or
Postgres.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
os.environ.setdefault("OPENAI_KEY", "test-openai-key")
os.environ.setdefault("DB_READONLY_URL", "postgresql://hive_readonly:test@localhost:5432/postgres")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("AGENT_API_KEYS", "test-agent-key-one,test-agent-key-two")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
