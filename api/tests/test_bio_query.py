"""Deterministic biological query generator: parse cases, sql_guard
compatibility, and injection resistance. The generator gets NO special trust —
everything it emits must survive guard_and_limit_sql like the LLM path."""

import sqlglot
from app.bio_query import generate_bio_sql
from app.sql_guard import guard_and_limit_sql
from sqlglot import exp


def _guarded(q: str) -> str:
    return guard_and_limit_sql(generate_bio_sql(q), 100)


def test_phospho_site_query():
    sql = generate_bio_sql("phospho STAT3 Tyr705")
    assert "modification_type ILIKE '%phospho%'" in sql
    assert "residue ILIKE 'Tyr' AND residue_position = 705" in sql
    assert "%STAT3%" in sql  # remaining term matched across bio columns
    assert "Tyr705" not in sql.replace("residue", "")  # site consumed, not a term
    _guarded("phospho STAT3 Tyr705")  # must pass the guard


def test_one_letter_site():
    sql = generate_bio_sql("phospho AKT S473")
    assert "residue ILIKE 'Ser' AND residue_position = 473" in sql
    assert "%AKT%" in sql


def test_vendor_catalog():
    sql = generate_bio_sql("CST 9145")
    assert "antibody_vendor ILIKE '%cell signaling%'" in sql
    assert "antibody_catalog_number ILIKE '%9145%'" in sql
    _guarded("CST 9145")


def test_hash_catalog_without_vendor():
    sql = generate_bio_sql("antibody #9134")
    assert "antibody_catalog_number ILIKE '%9134%'" in sql


def test_bare_number_without_vendor_is_not_catalog():
    # A number with no vendor and no '#' is NOT trusted as a catalog number.
    sql = generate_bio_sql("9145")
    assert "antibody_catalog_number" not in sql


def test_coip():
    sql = generate_bio_sql("co-IP EGFR")
    assert "experiment_type ILIKE 'co_ip'" in sql
    assert "%EGFR%" in sql
    _guarded("co-IP EGFR")


def test_cell_line_and_protein_terms_are_anded():
    sql = generate_bio_sql("A549 STAT3")
    # Two independent term groups, AND'd; each ORs across the bio columns.
    assert sql.count("cell_line ILIKE") == 2
    assert " AND " in sql


def test_loading_control_and_needs_review():
    sql = generate_bio_sql("loading control needs review")
    assert "experiment_type ILIKE 'loading_control'" in sql
    assert "needs_review = true" in sql


def test_stopwords_dropped():
    sql = generate_bio_sql("show me western blot evidence for STAT3 in cells")
    assert "%STAT3%" in sql
    for w in ("western", "blot", "evidence", "cells"):
        assert f"%{w}%" not in sql.lower()


def test_empty_query_is_a_plain_select():
    sql = generate_bio_sql("   ")
    assert sql.strip().upper().startswith("SELECT * FROM")
    assert "WHERE" not in sql.upper()
    _guarded("   ")


def test_injection_attempt_is_neutralized():
    hostile = "STAT3'; DROP TABLE western_blot_records; --"
    sql = generate_bio_sql(hostile)
    # The hostile text is demoted to harmless ILIKE search literals: the result
    # is exactly one plain SELECT, with no Drop/Command nodes anywhere, and it
    # still passes the guard. ("DROP" MAY appear inside a quoted '%DROP%'
    # literal — that is a search term, not a statement.)
    stmts = sqlglot.parse(sql, read="postgres")
    assert len(stmts) == 1 and isinstance(stmts[0], exp.Select)
    assert not list(stmts[0].find_all(exp.Drop, exp.Command))
    guarded = guard_and_limit_sql(sql, 10)
    assert isinstance(sqlglot.parse_one(guarded, read="postgres"), exp.Select)


def test_settled_evidence_ordered_first():
    assert "ORDER BY needs_review ASC" in generate_bio_sql("STAT3")


def test_p_prefix_term_does_not_add_phospho_filter():
    # Regression: "P-ERK" used to add modification_type ILIKE '%phospho%',
    # which EXCLUDED the P-ERK rows whose modification is honestly
    # CONFLICTING (null scalar). The prefix term matches the printed label;
    # no modification filter may be inferred from it.
    sql = generate_bio_sql("needs review P-ERK")
    assert "modification_type" not in sql
    assert "%P-ERK%" in sql and "needs_review = true" in sql
    _guarded("needs review P-ERK")


def test_phospho_word_filter_includes_unsettled():
    # An explicit phospho search must SURFACE disputed phospho-vs-total rows
    # (status CONFLICTING/AMBIGUOUS), not hide them behind the null scalar.
    sql = generate_bio_sql("phospho ERK")
    assert "modification_type ILIKE '%phospho%'" in sql
    assert "CONFLICTING" in sql and "AMBIGUOUS" in sql
    _guarded("phospho ERK")
