"""
Tests for the AST-level SQL validator that replaced the old backend's
`if "drop" in sql.lower()` substring blocklist.

Everything here calls guard_and_limit_sql for real rather than reasoning about
the code - sqlglot's AST shapes (particularly where LIMIT lives, and what
walk() yields) are easy to get subtly wrong, and a guard that silently stops
matching is worse than no guard.
"""

import pytest
import sqlglot
from sqlglot import exp

from app.config import settings
from app.sql_guard import SQLGuardError, guard_and_limit_sql

TABLE = settings.table_name


def limit_of(sql: str) -> int:
    """The LIMIT actually present in the returned SQL, parsed back out."""
    node = sqlglot.parse_one(sql, read="postgres").args.get("limit")
    assert node is not None, f"no LIMIT in {sql!r}"
    return int(node.expression.this)


# --- the happy path ------------------------------------------------------


def test_normal_query_passes_and_gets_a_limit():
    out = guard_and_limit_sql(f"SELECT * FROM {TABLE} WHERE target ILIKE '%p53%'", 100)

    assert limit_of(out) == 100
    assert "ILIKE" in out.upper()
    assert TABLE in out


def test_schema_qualified_table_is_allowed():
    out = guard_and_limit_sql(f"SELECT * FROM public.{TABLE}", 10)

    assert limit_of(out) == 10


def test_multi_condition_and_or_passes():
    # Regression: sqlglot >= 30 models AND/OR as exp.Func subclasses
    # (exp.Connector); the function allowlist must not reject boolean
    # connectors, or every multi-concept query (which nlp.py's prompt rules
    # 5/6/8 explicitly instruct the model to produce) 400s.
    out = guard_and_limit_sql(
        f"SELECT * FROM {TABLE} WHERE (target ILIKE '%stat3%' OR canonical_target "
        f"ILIKE '%stat3%') AND (treatment_context ILIKE '%il-6%' OR condition "
        f"ILIKE '%il-6%')",
        50,
    )
    assert limit_of(out) == 50
    assert " AND " in out.upper()
    assert " OR " in out.upper()


def test_connector_skip_does_not_reopen_function_hole():
    # The Connector exemption must not exempt real functions nested inside
    # AND/OR expressions.
    with pytest.raises(SQLGuardError, match="not allowed"):
        guard_and_limit_sql(
            f"SELECT * FROM {TABLE} WHERE target ILIKE '%x%' AND pg_sleep(5) IS NULL",
            10,
        )


def test_trailing_semicolon_and_whitespace_are_tolerated():
    out = guard_and_limit_sql(f"  SELECT * FROM {TABLE};  ", 10)

    assert limit_of(out) == 10


def test_allowed_functions_pass():
    out = guard_and_limit_sql(f"SELECT COUNT(*) FROM {TABLE} WHERE LOWER(target) = 'p53'", 10)

    assert limit_of(out) == 10


# --- LIMIT enforcement ---------------------------------------------------


def test_missing_limit_gets_the_requested_one():
    assert limit_of(guard_and_limit_sql(f"SELECT * FROM {TABLE}", 42)) == 42


def test_limit_above_max_is_clamped_to_max():
    huge = settings.max_search_limit * 100
    out = guard_and_limit_sql(f"SELECT * FROM {TABLE} LIMIT {huge}", huge)

    assert limit_of(out) == settings.max_search_limit


def test_model_generated_limit_cannot_exceed_the_requested_limit():
    """The LLM asking for more rows than the caller did doesn't win."""
    out = guard_and_limit_sql(f"SELECT * FROM {TABLE} LIMIT 5000", 25)

    assert limit_of(out) == 25


def test_smaller_model_limit_is_preserved():
    """min(model, requested, max) - a narrower query stays narrow."""
    out = guard_and_limit_sql(f"SELECT * FROM {TABLE} LIMIT 5", 100)

    assert limit_of(out) == 5


def test_requested_limit_is_floored_at_one():
    assert limit_of(guard_and_limit_sql(f"SELECT * FROM {TABLE}", 0)) == 1
    assert limit_of(guard_and_limit_sql(f"SELECT * FROM {TABLE}", -10)) == 1


# --- rejections ----------------------------------------------------------


def test_other_table_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql("SELECT * FROM auth.users", 10)


def test_joining_another_table_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT * FROM {TABLE} JOIN auth.users ON true", 10)


def test_subquery_against_another_table_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(
            f"SELECT * FROM {TABLE} WHERE paper_id IN (SELECT email FROM auth.users)", 10
        )


def test_cte_against_another_table_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql("WITH x AS (SELECT * FROM auth.users) SELECT * FROM x", 10)


def test_multiple_statements_are_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT * FROM {TABLE}; DROP TABLE {TABLE};", 10)


@pytest.mark.parametrize(
    "sql",
    [
        f"DROP TABLE {TABLE}",
        f"DELETE FROM {TABLE}",
        f"UPDATE {TABLE} SET target = 'x'",
        f"INSERT INTO {TABLE} (paper_id) VALUES ('x')",
        f"ALTER TABLE {TABLE} ADD COLUMN x TEXT",
        "CREATE TABLE evil (id INT)",
        f"TRUNCATE {TABLE}",
    ],
)
def test_non_select_statements_are_rejected(sql):
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(sql, 10)


def test_disallowed_function_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT pg_sleep(10) FROM {TABLE}", 10)


@pytest.mark.parametrize(
    "call",
    [
        "pg_read_file('/etc/passwd')",
        "dblink('', '')",
        "current_setting('is_superuser')",
        "query_to_xml('SELECT 1', true, true, '')",
    ],
)
def test_other_dangerous_functions_are_rejected(call):
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT {call} FROM {TABLE}", 10)


@pytest.mark.parametrize(
    "call",
    [
        "version()",
        "current_user",
        "session_user",
        "current_database()",
        "current_schema()",
        "now()",
        "md5(target)",
        "encode(target::bytea, 'hex')",
        "string_agg(target, ',')",
    ],
)
def test_functions_sqlglot_has_a_node_type_for_are_still_rejected(call):
    """
    Regression test for a real hole: the allowlist originally only inspected
    exp.Anonymous nodes, so anything sqlglot parses into a dedicated class
    (version() -> CurrentVersion, md5() -> MD5, string_agg() -> GroupConcat)
    bypassed it completely. These leak DB/session metadata rather than table
    data, but the allowlist is supposed to be deny-by-default, and the set of
    functions sqlglot types grows every release.
    """
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT {call} FROM {TABLE}", 10)


def test_set_returning_function_in_from_is_rejected():
    """generate_series() in FROM isn't an exp.Table, so only the function
    allowlist stands between it and execution."""
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT * FROM {TABLE}, generate_series(1, 10)", 10)


def test_top_level_union_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT * FROM {TABLE} UNION SELECT email FROM auth.users", 10)


def test_nested_union_is_rejected():
    """
    Guards the walk() branch specifically. A top-level UNION is already caught
    by the "must be a Select" check, so it wouldn't notice if walk() stopped
    yielding matchable nodes; a UNION buried in a subquery only fails if the
    DISALLOWED_NODE_TYPES walk is really working.
    """
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(
            f"SELECT * FROM {TABLE} WHERE id IN "
            f"(SELECT id FROM {TABLE} UNION SELECT id FROM {TABLE})",
            10,
        )


def test_select_into_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql(f"SELECT * INTO evil FROM {TABLE}", 10)


def test_tableless_select_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql("SELECT 1", 10)


def test_unparseable_sql_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql("this is not sql at all ((((", 10)


def test_empty_sql_is_rejected():
    with pytest.raises(SQLGuardError):
        guard_and_limit_sql("   ", 10)


# --- regression guards for the guard itself ------------------------------


def test_walk_still_yields_expressions():
    """
    If a sqlglot upgrade changed walk() back to yielding (node, parent, key)
    tuples, every isinstance(node, DISALLOWED_NODE_TYPES) check in the guard
    would silently stop matching. Fail loudly here instead.
    """
    parsed = sqlglot.parse_one(f"SELECT * FROM {TABLE}", read="postgres")

    assert all(isinstance(n, exp.Expression) for n in parsed.walk())
