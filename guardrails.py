import re


# =========================================
# DATASET GUARDRAIL
# =========================================

def validate_dataset(df):

    errors = []

    if df.empty:
        errors.append(
            "Dataset is empty."
        )

    if len(df) > 1_000_000:
        errors.append(
            "Dataset is too large. "
            "Maximum allowed rows: 1,000,000."
        )

    if len(df.columns) > 200:
        errors.append(
            "Dataset contains too many columns."
        )

    if df.columns.duplicated().any():
        errors.append(
            "Dataset contains duplicate columns."
        )

    if errors:
        return False, errors

    return True, []


# =========================================
# QUESTION GUARDRAIL
# =========================================

def validate_question(question):

    if not question:
        return False, "Question cannot be empty."

    question = question.strip()

    if len(question) > 1000:
        return False, (
            "Question is too long. "
            "Maximum length is 1000 characters."
        )

    suspicious_patterns = [
        r"ignore previous instructions",
        r"ignore all instructions",
        r"ignore your instructions",
        r"system prompt",
        r"developer message",
        r"reveal your prompt",
        r"show your instructions",
        r"jailbreak"
    ]

    for pattern in suspicious_patterns:

        if re.search(
            pattern,
            question,
            re.IGNORECASE
        ):
            return False, (
                "Question rejected by security guardrail."
            )

    return True, ""


# =========================================
# SQL GUARDRAIL
# =========================================

def validate_sql(sql_query):

    if not sql_query:
        return False, "SQL query is empty."

    sql = sql_query.strip().lower()

    # Remove trailing semicolon
    sql = sql.rstrip(";").strip()

    # Only SELECT
    if not sql.startswith("select"):
        return False, (
            "Only SELECT queries are allowed."
        )

    forbidden_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "replace",
        "attach",
        "detach",
        "pragma",
        "vacuum"
    ]

    for keyword in forbidden_keywords:

        if re.search(
            rf"\b{keyword}\b",
            sql
        ):
            return False, (
                f"Forbidden SQL operation: {keyword}"
            )

    # Multiple statements
    if ";" in sql:

        return False, (
            "Multiple SQL statements are not allowed."
        )

    # Prevent access to SQLite metadata
    forbidden_tables = [
        "sqlite_master",
        "sqlite_schema",
        "sqlite_temp_master"
    ]

    for table in forbidden_tables:

        if table in sql:
            return False, (
                "Access to database metadata "
                "is not allowed."
            )

    return True, ""