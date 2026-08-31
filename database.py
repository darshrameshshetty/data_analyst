import re

from sqlalchemy import (
    create_engine,
    text
)


# =========================================
# CLEAN COLUMN NAME
# =========================================

def clean_column_name(column):

    column = str(column)

    column = column.strip()

    column = column.lower()

    column = re.sub(
        r"[^a-zA-Z0-9_]",
        "_",
        column
    )

    column = re.sub(
        r"_+",
        "_",
        column
    )

    column = column.strip("_")

    if not column:
        column = "column"

    if column[0].isdigit():

        column = (
            "col_" + column
        )

    return column


# =========================================
# MAKE COLUMN NAMES UNIQUE
# =========================================

def make_unique_columns(columns):

    seen = {}

    result = []

    for column in columns:

        if column not in seen:

            seen[column] = 0
            result.append(column)

        else:

            seen[column] += 1

            new_name = (
                f"{column}_{seen[column]}"
            )

            result.append(new_name)

    return result


# =========================================
# CLEAN DATASET
# =========================================

def clean_dataset(df):

    df = df.copy()

    # Remove completely empty rows
    df = df.dropna(
        how="all"
    )

    # Remove duplicate rows
    df = df.drop_duplicates()

    # Clean column names
    columns = [
        clean_column_name(column)
        for column in df.columns
    ]

    # Make them unique
    columns = make_unique_columns(
        columns
    )

    df.columns = columns

    return df


# =========================================
# CREATE DATABASE
# =========================================

def create_database(df):

    engine = create_engine(
        "sqlite:///:memory:"
    )

    df.to_sql(
        "user_data",
        engine,
        index=False,
        if_exists="replace"
    )

    return engine


# =========================================
# GET SCHEMA
# =========================================

def get_schema(df):

    schema = []

    for column in df.columns:

        dtype = str(
            df[column].dtype
        )

        schema.append(
            f"{column}: {dtype}"
        )

    return "\n".join(schema)


# =========================================
# EXECUTE SQL
# =========================================

def execute_query(
    engine,
    sql_query
):

    with engine.connect() as connection:

        result = connection.execute(
            text(sql_query)
        )

        rows = result.fetchall()

        columns = list(
            result.keys()
        )

    data = [
        dict(
            zip(columns, row)
        )
        for row in rows
    ]

    return data