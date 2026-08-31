import os
import streamlit as st

# Get API key from Streamlit Cloud Secrets
os.environ["MISTRAL_API_KEY"] = st.secrets["MISTRAL_API_KEY"]

import pandas as pd
import plotly.express as px
import uuid
from datetime import datetime

# Import LangGraph AFTER setting the API key
from graph import app



# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# SESSION STATE
# =========================================================

if "chats" not in st.session_state:

    st.session_state.chats = {}


if "current_chat_id" not in st.session_state:

    chat_id = str(uuid.uuid4())

    st.session_state.chats[chat_id] = {

        "title": "New Chat",

        "messages": [],

        "df": None,

        "filename": None,

        "created_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    }

    st.session_state.current_chat_id = chat_id


# =========================================================
# CREATE NEW CHAT
# =========================================================

def create_new_chat():

    chat_id = str(uuid.uuid4())

    st.session_state.chats[chat_id] = {

        "title": "New Chat",

        "messages": [],

        "df": None,

        "filename": None,

        "created_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    }

    st.session_state.current_chat_id = chat_id


# =========================================================
# CURRENT CHAT
# =========================================================

current_chat = st.session_state.chats[
    st.session_state.current_chat_id
]


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("💬 AI Data Analyst")


    # =====================================================
    # NEW CHAT
    # =====================================================

    if st.button(
        "➕ New Chat",
        use_container_width=True
    ):

        create_new_chat()

        st.rerun()


    st.divider()


    # =====================================================
    # PREVIOUS CHATS
    # =====================================================

    st.subheader(
        "Previous Chats"
    )


    chat_items = list(
        st.session_state.chats.items()
    )


    # Newest first

    chat_items.reverse()


    for chat_id, chat in chat_items:

        col1, col2 = st.columns(
            [5, 1]
        )


        # -----------------------------------------------
        # CHAT BUTTON
        # -----------------------------------------------

        with col1:

            title = chat["title"]


            if not title:

                title = "New Chat"


            if st.button(
                title,
                key=f"chat_{chat_id}",
                use_container_width=True
            ):

                st.session_state.current_chat_id = (
                    chat_id
                )

                st.rerun()


        # -----------------------------------------------
        # DELETE CHAT
        # -----------------------------------------------

        with col2:

            if st.button(
                "🗑️",
                key=f"delete_{chat_id}"
            ):

                del st.session_state.chats[
                    chat_id
                ]


                # If no chats remain

                if not st.session_state.chats:

                    create_new_chat()


                else:

                    # Select latest remaining chat

                    st.session_state.current_chat_id = (
                        list(
                            st.session_state.chats.keys()
                        )[-1]
                    )


                st.rerun()


    st.divider()


    # =====================================================
    # CLEAR ALL CHATS
    # =====================================================

    if st.button(
        "🗑️ Clear All Chats",
        use_container_width=True
    ):

        st.session_state.chats = {}

        create_new_chat()

        st.rerun()


# =========================================================
# MAIN PAGE
# =========================================================

st.title(
    "📊 AI-Powered Data Analyst Agent"
)

st.caption(
    "Upload a CSV or Excel dataset and ask "
    "questions using natural language."
)


# =========================================================
# FILE UPLOADER
# =========================================================

uploaded_file = st.file_uploader(

    "Upload CSV or Excel dataset",

    type=[
        "csv",
        "xlsx"
    ],

    key=f"upload_{st.session_state.current_chat_id}"
)


# =========================================================
# READ DATASET
# =========================================================

if uploaded_file:

    # Only load a new dataset when the filename changes

    if (
        current_chat["filename"]
        != uploaded_file.name
    ):

        try:

            if uploaded_file.name.endswith(
                ".csv"
            ):

                df = pd.read_csv(
                    uploaded_file
                )

            else:

                df = pd.read_excel(
                    uploaded_file
                )


            # Save dataset to current chat

            current_chat["df"] = df

            current_chat["filename"] = (
                uploaded_file.name
            )


        except Exception as e:

            st.error(
                f"Could not read file: {e}"
            )

            st.stop()


    else:

        df = current_chat["df"]


else:

    df = current_chat["df"]


# =========================================================
# DATASET INFORMATION
# =========================================================

if df is not None:

    st.subheader(
        "📁 Dataset"
    )


    st.write(
        f"**File:** {current_chat['filename']}"
    )


    # =====================================================
    # DATASET PREVIEW
    # =====================================================

    with st.expander(
        "View Dataset Preview",
        expanded=False
    ):

        st.dataframe(
            df.head(10),
            use_container_width=True
        )


    # =====================================================
    # DATASET METRICS
    # =====================================================

    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Rows",
            len(df)
        )


    with col2:

        st.metric(
            "Columns",
            len(df.columns)
        )


    with col3:

        st.metric(

            "Missing Values",

            int(
                df.isna()
                .sum()
                .sum()
            )
        )


# =========================================================
# DISPLAY CHAT HISTORY
# =========================================================

for message in current_chat["messages"]:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


        # =================================================
        # DISPLAY RESULT TABLE
        # =================================================

        message_result = message.get(
            "result",
            []
        )


        if message_result:

            result_df = pd.DataFrame(
                message_result
            )


            st.dataframe(
                result_df,
                use_container_width=True
            )


        # =================================================
        # DISPLAY CHART
        # =================================================

        chart_plan = message.get(
            "chart_plan",
            {}
        )


        if chart_plan:

            chart_type = chart_plan.get(
                "chart_type",
                "none"
            )


            if chart_type != "none" and message_result:

                try:

                    result_df = pd.DataFrame(
                        message_result
                    )


                    x = chart_plan.get(
                        "x"
                    )

                    y = chart_plan.get(
                        "y"
                    )

                    title = chart_plan.get(
                        "title",
                        "Data Visualization"
                    )


                    # -------------------------------------
                    # Validate columns
                    # -------------------------------------

                    if (
                        x in result_df.columns
                        and y in result_df.columns
                    ):


                        # ---------------------------------
                        # BAR
                        # ---------------------------------

                        if chart_type == "bar":

                            fig = px.bar(

                                result_df,

                                x=x,

                                y=y,

                                title=title
                            )


                        # ---------------------------------
                        # LINE
                        # ---------------------------------

                        elif chart_type == "line":

                            fig = px.line(

                                result_df,

                                x=x,

                                y=y,

                                title=title
                            )


                        # ---------------------------------
                        # PIE
                        # ---------------------------------

                        elif chart_type == "pie":

                            fig = px.pie(

                                result_df,

                                names=x,

                                values=y,

                                title=title
                            )


                        # ---------------------------------
                        # SCATTER
                        # ---------------------------------

                        elif chart_type == "scatter":

                            fig = px.scatter(

                                result_df,

                                x=x,

                                y=y,

                                title=title
                            )


                        else:

                            fig = None


                        if fig:

                            st.plotly_chart(

                                fig,

                                use_container_width=True
                            )


                except Exception:

                    pass


# =========================================================
# CHAT INPUT
# =========================================================

question = st.chat_input(
    "Ask a question about your data..."
)


# =========================================================
# PROCESS QUESTION
# =========================================================

if question:


    # =====================================================
    # CHECK DATASET
    # =====================================================

    if df is None:

        st.warning(
            "Please upload a CSV or Excel "
            "dataset first."
        )

        st.stop()


    # =====================================================
    # CREATE CHAT TITLE
    # =====================================================

    if current_chat["title"] == "New Chat":

        current_chat["title"] = (

            question[:35]

            + (
                "..."
                if len(question) > 35
                else ""
            )
        )


    # =====================================================
    # IMPORTANT:
    # SAVE PREVIOUS CONVERSATION
    # BEFORE ADDING CURRENT QUESTION
    # =====================================================

    conversation_history = (

        current_chat["messages"].copy()

    )


    # =====================================================
    # SAVE USER MESSAGE
    # =====================================================

    current_chat["messages"].append(

        {
            "role": "user",

            "content": question
        }

    )


    # =====================================================
    # DISPLAY USER MESSAGE
    # =====================================================

    with st.chat_message(
        "user"
    ):

        st.markdown(
            question
        )


    # =====================================================
    # RUN LANGGRAPH
    # =====================================================

    with st.chat_message(
        "assistant"
    ):

        with st.spinner(
            "AI agent is analyzing your dataset..."
        ):

            try:

                result = app.invoke(

                    {

                        "df": df,

                        "question": question,

                        "conversation_history":
                            conversation_history,

                        "sql_retry_count": 0

                    }

                )


            except Exception as e:

                st.error(
                    f"Agent error: {e}"
                )

                # Save error to chat

                current_chat["messages"].append(

                    {

                        "role": "assistant",

                        "content":
                            f"⚠️ Agent error: {e}"

                    }

                )

                st.stop()


        # =================================================
        # CHECK ERROR
        # =================================================

        if result.get(
            "error"
        ):

            answer = (

                "⚠️ "

                + result["error"]

            )


            st.error(
                result["error"]
            )


            current_chat["messages"].append(

                {

                    "role": "assistant",

                    "content": answer

                }

            )

            st.stop()


        # =================================================
        # AI ANSWER
        # =================================================

        answer = result.get(

            "final_answer",

            "No answer generated."

        )


        st.markdown(
            answer
        )


        # =================================================
        # QUERY RESULT
        # =================================================

        query_result = result.get(

            "query_result",

            []

        )


        result_df = None


        if query_result:


            result_df = pd.DataFrame(

                query_result

            )


            st.subheader(
                "📋 Analysis Result"
            )


            st.dataframe(

                result_df,

                use_container_width=True

            )


        # =================================================
        # CHART
        # =================================================

        chart_plan = result.get(

            "chart_plan",

            {}

        )


        chart_type = chart_plan.get(

            "chart_type",

            "none"

        )


        if (

            result_df is not None

            and not result_df.empty

            and chart_type != "none"

        ):


            x = chart_plan.get(
                "x"
            )

            y = chart_plan.get(
                "y"
            )

            title = chart_plan.get(

                "title",

                "Data Visualization"

            )


            try:


                # -----------------------------------------
                # Validate chart columns
                # -----------------------------------------

                if (

                    x in result_df.columns

                    and y in result_df.columns

                ):


                    # -------------------------------------
                    # BAR
                    # -------------------------------------

                    if chart_type == "bar":

                        fig = px.bar(

                            result_df,

                            x=x,

                            y=y,

                            title=title

                        )


                    # -------------------------------------
                    # LINE
                    # -------------------------------------

                    elif chart_type == "line":

                        fig = px.line(

                            result_df,

                            x=x,

                            y=y,

                            title=title

                        )


                    # -------------------------------------
                    # PIE
                    # -------------------------------------

                    elif chart_type == "pie":

                        fig = px.pie(

                            result_df,

                            names=x,

                            values=y,

                            title=title

                        )


                    # -------------------------------------
                    # SCATTER
                    # -------------------------------------

                    elif chart_type == "scatter":

                        fig = px.scatter(

                            result_df,

                            x=x,

                            y=y,

                            title=title

                        )


                    else:

                        fig = None


                    if fig:

                        st.subheader(
                            "📊 Visualization"
                        )


                        st.plotly_chart(

                            fig,

                            use_container_width=True

                        )


            except Exception as e:

                st.warning(

                    "Chart could not be generated: "

                    f"{e}"

                )


        # =================================================
        # SAVE ASSISTANT MESSAGE
        # =================================================

        current_chat["messages"].append(

            {

                "role": "assistant",

                "content": answer,

                "result": query_result,

                "chart_plan": chart_plan,

                "sql_query": result.get(

                    "sql_query",

                    ""

                )

            }

        )


# =========================================================
# ABOUT PROJECT
# =========================================================

with st.expander(
    "ℹ️ About this project"
):

    st.write(

        """

        This application is a conversational
        AI Data Analyst Agent.

        The user uploads a CSV or Excel dataset
        and interacts with the data using
        natural language.

        Technologies:

        • Python
        • Pandas
        • SQLite
        • LangChain
        • LangGraph
        • Mistral AI
        • Streamlit
        • Plotly
        • Guardrails

        The LangGraph workflow:

        1. Dataset validation
        2. Dataset cleaning
        3. Database creation
        4. Question validation
        5. Natural language → SQL
        6. SQL validation
        7. SQL execution
        8. Automatic chart planning
        9. Business insight generation

        The application also supports:

        • Multiple conversations
        • Conversation history
        • Follow-up questions
        • Dataset-specific chats
        • Automatic visualizations

        """

    )

