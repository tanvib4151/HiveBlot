"""
Validates and constrains LLM-generated SQL before it ever reaches a database
connection, replacing a substring blocklist (`if "drop" in sql.lower()`)
with real AST-level checks via sqlglot.

This is a second layer of defense, not the only one: the query this
validates should also only ever run through a Postgres role scoped to
SELECT on `western_blot_records` (see db.py), so a bug here can't turn
into a full-database compromise.
"""

import sqlglot
from sqlglot import exp

from .config import settings


class SQLGuardError(ValueError):
    pass


# Only functions the generated SQL is realistically expected to need for
# ILIKE-based text search. Anything not in this list is rejected, which
# blocks pg_sleep(), dblink(), pg_read_file(), etc. by construction rather
# than by trying to enumerate every dangerous function.
#
# Names are matched against sqlglot's canonical name for the node, so the
# spelling here is the SQL one ("current_user", not "currentuser").
ALLOWED_FUNCTIONS = {"lower", "upper", "coalesce", "count", "cast"}

# Node types that mean this isn't a plain, single SELECT.
DISALLOWED_NODE_TYPES = (
    exp.Union,
    exp.Except,
    exp.Intersect,
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Into,
)


def _function_name(func: exp.Func) -> str:
    """
    The SQL-level name of a function node, lowercased.

    sqlglot parses functions it knows into dedicated node types (version() ->
    exp.CurrentVersion, md5() -> exp.MD5, ...) and everything else into
    exp.Anonymous. Checking only Anonymous nodes would let every function
    sqlglot happens to have a class for straight through the allowlist - and
    that set grows with each sqlglot release - so both shapes are resolved to
    a name here and checked the same way.
    """
    if isinstance(func, exp.Anonymous):
        return str(func.this).lower()
    try:
        return func.sql_names()[0].lower()
    except (AttributeError, IndexError):
        # Unnamed/unexpected node: fall back to the class name, which won't
        # be in the allowlist, so it gets rejected rather than waved through.
        return type(func).__name__.lower()


def guard_and_limit_sql(raw_sql: str, requested_limit: int) -> str:
    """
    Raises SQLGuardError if raw_sql is anything other than a single SELECT
    against settings.table_name. Otherwise returns the SQL rewritten with a
    server-enforced LIMIT, ignoring whatever (if anything) the LLM put there.
    """
    cleaned = raw_sql.strip().rstrip(";")

    try:
        statements = [s for s in sqlglot.parse(cleaned, read="postgres") if s is not None]
    except Exception as e:
        raise SQLGuardError(f"Could not parse generated SQL: {e}") from e

    if len(statements) != 1:
        raise SQLGuardError("Exactly one SQL statement is required")

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        raise SQLGuardError("Only SELECT statements are allowed")

    for node in stmt.walk():
        if isinstance(node, DISALLOWED_NODE_TYPES):
            raise SQLGuardError(f"'{type(node).__name__}' is not allowed in a search query")

    tables = {t.name.lower() for t in stmt.find_all(exp.Table)}
    if not tables:
        raise SQLGuardError("Query must reference a table")
    if tables != {settings.table_name.lower()}:
        raise SQLGuardError(f"Query may only reference {settings.table_name}")

    for func in stmt.find_all(exp.Func):
        # Boolean connectors (AND / OR) subclass exp.Func in sqlglot >= 30
        # (exp.Connector), but they are operators, not callable functions —
        # without this skip, EVERY multi-condition WHERE clause (which the
        # nlp.py prompt explicitly instructs the model to produce) is rejected.
        if isinstance(func, exp.Connector):
            continue
        name = _function_name(func)
        if name not in ALLOWED_FUNCTIONS:
            raise SQLGuardError(f"Function '{name}' is not allowed")

    limit_value = max(1, min(requested_limit, settings.max_search_limit))
    existing_limit_node = stmt.args.get("limit")
    if existing_limit_node is not None:
        try:
            existing_value = int(str(existing_limit_node.expression.this))
            limit_value = min(existing_value, limit_value)
        except (AttributeError, ValueError):
            pass

    stmt.set("limit", exp.Limit(expression=exp.Literal.number(limit_value)))

    return stmt.sql(dialect="postgres")
