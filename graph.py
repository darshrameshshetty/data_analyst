
from typing import TypedDict, Any
import json

from dotenv import load_dotenv

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langchain_mistralai import ChatMistralAI

from database import (
    clean_dataset,
    create_database,
    get_schema,
    execute_query
)

from guardrails import (
    validate_dataset,
    validate_question,
    validate_sql
)


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# LLM
# =========================================================

llm = ChatMistralAI(
    model="mistral-small-latest",
    temperature=0
)


# =========================================================
# STATE
# =========================================================

class AnalyticsState(TypedDict, total=False):

    # Dataset
    df: Any

    # Database
    engine: Any

    # User question
    question: str

    # Previous conversation
    conversation_history: list

    # Database schema
    schema: str

    # SQL
    sql_query: str

    # SQL result
    query_result: Any

    # Visualization
    chart_plan: dict

    # Final answer
    final_answer: str

    # Error
    error: str

    # Retry counter
    sql_retry_count: int

    # Guardrail status
    guardrail_passed: bool


# =========================================================
# NODE 1
# DATASET GUARDRAIL
# =========================================================

def dataset_guardrail(state):

    df = state["df"]

    valid, errors = validate_dataset(
        df
    )

    if not valid:

        return {
            "guardrail_passed": False,
            "error": "\n".join(errors)
        }

    return {
        "guardrail_passed": True,
        "error": ""
    }


# =========================================================
# NODE 2
# LOAD DATASET
# =========================================================

def load_dataset(state):

    df = state["df"]

    # Clean dataset
    df = clean_dataset(
        df
    )

    # Create SQLite database
    engine = create_database(
        df
    )

    # Get database schema
    schema = get_schema(
        df
    )

    return {
        "df": df,
        "engine": engine,
        "schema": schema
    }


# =========================================================
# NODE 3
# QUESTION GUARDRAIL
# =========================================================

def question_guardrail(state):

    question = state["question"]

    valid, error = validate_question(
        question
    )

    if not valid:

        return {
            "guardrail_passed": False,
            "error": error
        }

    return {
        "guardrail_passed": True,
        "error": ""
    }


# =========================================================
# HELPER
# CONVERT CHAT HISTORY TO TEXT
# =========================================================

def format_history(history):

    if not history:

        return "No previous conversation."


    history_text = ""

    for message in history[-10:]:

        role = message.get(
            "role",
            ""
        )

        content = message.get(
            "content",
            ""
        )

        history_text += (
            f"{role}: {content}\n"
        )

    return history_text


# =========================================================
# NODE 4
# GENERATE SQL
# =========================================================

def generate_sql(state):

    question = state["question"]

    schema = state["schema"]

    history = state.get(
        "conversation_history",
        []
    )

    history_text = format_history(
        history
    )


    prompt = f"""
You are a professional data analyst.

Your job is to convert the user's
natural-language question into SQLite SQL.

The user may ask follow-up questions.

You MUST use the previous conversation
to understand references such as:

- it
- its
- they
- them
- that
- those
- the previous result
- the same region
- the same product
- that category
- the above result

--------------------------------------------------
PREVIOUS CONVERSATION
--------------------------------------------------

{history_text}

--------------------------------------------------
CURRENT USER QUESTION
--------------------------------------------------

{question}

--------------------------------------------------
DATABASE
--------------------------------------------------

Table name:

user_data

Schema:

{schema}

--------------------------------------------------
SQL RULES
--------------------------------------------------

1. Return ONLY one SQL SELECT query.

2. Use only the table:

user_data

3. Use only columns present in the schema.

4. Never modify the database.

5. Never use INSERT.

6. Never use UPDATE.

7. Never use DELETE.

8. Never use DROP.

9. Never use ALTER.

10. Never use CREATE.

11. Never access SQLite metadata.

12. Do not use other tables.

13. Do not invent columns.

14. For detailed results use:

LIMIT 100

15. If aggregation is appropriate,
prefer SUM, AVG, COUNT, MIN or MAX.

16. If the user asks for a ranking,
use ORDER BY and LIMIT.

17. If the user asks about a trend over time,
group the data by the appropriate date/time column.

Return ONLY SQL.

SQL:
"""


    try:

        response = llm.invoke(
            prompt
        )

        sql_query = response.content.strip()

        sql_query = sql_query.replace(
            "```sql",
            ""
        )

        sql_query = sql_query.replace(
            "```",
            ""
        )

        return {
            "sql_query": sql_query.strip(),
            "error": ""
        }


    except Exception as e:

        return {
            "sql_query": "",
            "error": f"LLM error: {str(e)}",
            "guardrail_passed": False
        }


# =========================================================
# NODE 5
# SQL GUARDRAIL
# =========================================================

def sql_guardrail(state):

    sql_query = state.get(
        "sql_query",
        ""
    )

    if not sql_query:

        return {
            "guardrail_passed": False,
            "error": "No SQL query was generated."
        }


    valid, error = validate_sql(
        sql_query
    )

    if not valid:

        return {
            "guardrail_passed": False,
            "error": error
        }


    return {
        "guardrail_passed": True,
        "error": ""
    }


# =========================================================
# NODE 6
# EXECUTE SQL
# =========================================================

def execute_sql(state):

    engine = state["engine"]

    sql_query = state["sql_query"]


    try:

        result = execute_query(
            engine,
            sql_query
        )


        return {
            "query_result": result,
            "error": "",
            "guardrail_passed": True
        }


    except Exception as e:

        return {
            "query_result": [],
            "error": str(e),
            "guardrail_passed": False
        }


# =========================================================
# NODE 7
# FIX SQL
# =========================================================

def fix_sql(state):

    question = state["question"]

    schema = state["schema"]

    old_sql = state.get(
        "sql_query",
        ""
    )

    error = state.get(
        "error",
        ""
    )

    retry_count = state.get(
        "sql_retry_count",
        0
    )


    history = state.get(
        "conversation_history",
        []
    )

    history_text = format_history(
        history
    )


    prompt = f"""
You are debugging a SQLite query.

The query generated by another AI
failed during execution.

--------------------------------------------------
PREVIOUS CONVERSATION
--------------------------------------------------

{history_text}

--------------------------------------------------
CURRENT QUESTION
--------------------------------------------------

{question}

--------------------------------------------------
DATABASE SCHEMA
--------------------------------------------------

{schema}

--------------------------------------------------
PREVIOUS SQL
--------------------------------------------------

{old_sql}

--------------------------------------------------
DATABASE ERROR
--------------------------------------------------

{error}

--------------------------------------------------
RULES
--------------------------------------------------

1. Return ONLY one SELECT query.

2. Use only:

user_data

3. Use only valid columns.

4. Do not modify the database.

5. No INSERT.

6. No UPDATE.

7. No DELETE.

8. No DROP.

9. No ALTER.

10. No CREATE.

11. No SQLite metadata.

12. Return executable SQLite SQL.

Return ONLY SQL.

Corrected SQL:
"""


    try:

        response = llm.invoke(
            prompt
        )

        sql_query = response.content.strip()

        sql_query = sql_query.replace(
            "```sql",
            ""
        )

        sql_query = sql_query.replace(
            "```",
            ""
        )


        return {
            "sql_query": sql_query.strip(),
            "sql_retry_count": retry_count + 1,
            "error": ""
        }


    except Exception as e:

        return {
            "sql_query": "",
            "sql_retry_count": retry_count + 1,
            "error": f"LLM error: {str(e)}"
        }


# =========================================================
# NODE 8
# GENERATE CHART PLAN
# =========================================================

def generate_chart_plan(state):

    question = state["question"]

    result = state.get(
        "query_result",
        []
    )


    if not result:

        return {
            "chart_plan": {
                "chart_type": "none"
            }
        }


    columns = list(
        result[0].keys()
    )


    prompt = f"""
You are a data visualization expert.

Determine the most useful visualization
for the user's question and query result.

--------------------------------------------------
USER QUESTION
--------------------------------------------------

{question}

--------------------------------------------------
QUERY RESULT
--------------------------------------------------

{result}

--------------------------------------------------
AVAILABLE COLUMNS
--------------------------------------------------

{columns}

--------------------------------------------------
ALLOWED CHART TYPES
--------------------------------------------------

bar
line
pie
scatter
none

--------------------------------------------------
RULES
--------------------------------------------------

1. Use "none" if visualization is not useful.

2. Use "bar" for category comparisons.

3. Use "line" for time-series trends.

4. Use "pie" for part-to-whole comparisons.

5. Use "scatter" for relationships between
two numeric variables.

6. x must be a valid result column.

7. y must be a valid numeric result column.

8. Do not invent columns.

9. Return ONLY valid JSON.

Example:

{{
    "chart_type": "bar",
    "x": "region",
    "y": "total_sales",
    "title": "Sales by Region"
}}

If no chart is useful:

{{
    "chart_type": "none"
}}
"""


    try:

        response = llm.invoke(
            prompt
        )

        content = response.content.strip()

        content = content.replace(
            "```json",
            ""
        )

        content = content.replace(
            "```",
            ""
        )


        plan = json.loads(
            content
        )


    except Exception:

        plan = {
            "chart_type": "none"
        }


    # =====================================================
    # VALIDATE CHART TYPE
    # =====================================================

    allowed_types = [
        "bar",
        "line",
        "pie",
        "scatter",
        "none"
    ]


    chart_type = plan.get(
        "chart_type",
        "none"
    )


    if chart_type not in allowed_types:

        plan = {
            "chart_type": "none"
        }


    # =====================================================
    # VALIDATE COLUMNS
    # =====================================================

    if plan.get(
        "chart_type"
    ) != "none":

        x = plan.get(
            "x"
        )

        y = plan.get(
            "y"
        )


        if (
            x not in columns
            or y not in columns
        ):

            plan = {
                "chart_type": "none"
            }


    return {
        "chart_plan": plan
    }


# =========================================================
# NODE 9
# ANALYZE RESULT
# =========================================================

def analyze_result(state):

    question = state["question"]

    result = state.get(
        "query_result",
        []
    )

    history = state.get(
        "conversation_history",
        []
    )


    history_text = format_history(
        history
    )


    prompt = f"""
You are a professional business analyst.

Use the previous conversation to
understand follow-up questions.

--------------------------------------------------
PREVIOUS CONVERSATION
--------------------------------------------------

{history_text}

--------------------------------------------------
CURRENT QUESTION
--------------------------------------------------

{question}

--------------------------------------------------
DATA ANALYSIS RESULT
--------------------------------------------------

{result}

--------------------------------------------------
INSTRUCTIONS
--------------------------------------------------

Provide a concise and useful answer.

Include:

1. Direct answer.

2. Important numbers.

3. Business insight when appropriate.

Do NOT invent information.

Only use information contained
in the data analysis result.

If there is no result,
say that no matching data was found.

If the question is a follow-up,
answer it in the context of the
previous conversation.
"""


    try:

        response = llm.invoke(
            prompt
        )

        return {
            "final_answer": response.content,
            "error": ""
        }


    except Exception as e:

        return {
            "final_answer": "",
            "error": f"LLM error: {str(e)}"
        }


# =========================================================
# ROUTING
# =========================================================

def route_dataset_guardrail(state):

    if state.get(
        "guardrail_passed"
    ):

        return "load_dataset"

    return "end"


# =========================================================

def route_question_guardrail(state):

    if state.get(
        "guardrail_passed"
    ):

        return "generate_sql"

    return "end"


# =========================================================

def route_sql_guardrail(state):

    if state.get(
        "guardrail_passed"
    ):

        return "execute_sql"


    retry_count = state.get(
        "sql_retry_count",
        0
    )


    if retry_count < 2:

        return "fix_sql"


    return "end"


# =========================================================

def route_execution(state):

    error = state.get(
        "error",
        ""
    )

    retry_count = state.get(
        "sql_retry_count",
        0
    )


    if not error:

        return "generate_chart_plan"


    if retry_count < 2:

        return "fix_sql"


    return "end"


# =========================================================
# BUILD GRAPH
# =========================================================

builder = StateGraph(
    AnalyticsState
)


# =========================================================
# ADD NODES
# =========================================================

builder.add_node(
    "dataset_guardrail",
    dataset_guardrail
)

builder.add_node(
    "load_dataset",
    load_dataset
)

builder.add_node(
    "question_guardrail",
    question_guardrail
)

builder.add_node(
    "generate_sql",
    generate_sql
)

builder.add_node(
    "sql_guardrail",
    sql_guardrail
)

builder.add_node(
    "execute_sql",
    execute_sql
)

builder.add_node(
    "fix_sql",
    fix_sql
)

builder.add_node(
    "generate_chart_plan",
    generate_chart_plan
)

builder.add_node(
    "analyze_result",
    analyze_result
)


# =========================================================
# EDGES
# =========================================================

builder.add_edge(
    START,
    "dataset_guardrail"
)


# Dataset guardrail
builder.add_conditional_edges(
    "dataset_guardrail",
    route_dataset_guardrail,
    {
        "load_dataset": "load_dataset",
        "end": END
    }
)


# Load dataset
builder.add_edge(
    "load_dataset",
    "question_guardrail"
)


# Question guardrail
builder.add_conditional_edges(
    "question_guardrail",
    route_question_guardrail,
    {
        "generate_sql": "generate_sql",
        "end": END
    }
)


# Generate SQL
builder.add_edge(
    "generate_sql",
    "sql_guardrail"
)


# SQL guardrail
builder.add_conditional_edges(
    "sql_guardrail",
    route_sql_guardrail,
    {
        "execute_sql": "execute_sql",
        "fix_sql": "fix_sql",
        "end": END
    }
)


# Execute SQL
builder.add_conditional_edges(
    "execute_sql",
    route_execution,
    {
        "generate_chart_plan":
            "generate_chart_plan",

        "fix_sql":
            "fix_sql",

        "end":
            END
    }
)


# Fix SQL → validate again
builder.add_edge(
    "fix_sql",
    "sql_guardrail"
)


# Chart → final answer
builder.add_edge(
    "generate_chart_plan",
    "analyze_result"
)


# Final answer → END
builder.add_edge(
    "analyze_result",
    END
)


# =========================================================
# COMPILE GRAPH
# =========================================================

app = builder.compile()

