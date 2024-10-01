import streamlit as st
import pandas as pd
from openai import OpenAI
from datetime import date, datetime, timedelta

from helper.db import initialize_and_create_connection
from helper.message import update_archived, update_pinned, generate_summary



st.set_page_config(page_title="DagBok", initial_sidebar_state="auto", page_icon="📖")

conn = initialize_and_create_connection(st)




st.sidebar.header("📅 Dagbok")

# NOTE: Journal - daily / weekly / monthly
is_filtered_by_date = st.sidebar.checkbox("Filtera datum")

date_selected = st.sidebar.date_input("Dates", "today")


st.sidebar.divider()

st.sidebar.header("📝 Projekt")

# NOTE: Project - open / closed / archived
is_filtered_by_project = st.sidebar.checkbox("Filtera Projekt")

with st.sidebar.expander("Skapa Nytt Projekt"):
    with st.form("new_project", border=False):
        project_name_input = st.text_input("Projekt namn")
        project_submit_button = st.form_submit_button("Skapa")

    if project_submit_button and project_name_input:
        with conn.session as s:
            s.execute(
                "INSERT INTO projects (name, timestamp) VALUES (:name, :timestamp);",
                params=dict(name=project_name_input, timestamp=datetime.now())
            )
            s.commit()

       

# Sort descending by timestamp
projects = conn.query("SELECT * FROM projects ORDER BY timestamp DESC")

if not projects.empty:
    st.session_state.projects = projects.to_dict(orient="records")
else:
    st.session_state.projects = []

# filter messages by project
project_id_selected = st.sidebar.radio("Projects", [project["id"] for project in st.session_state.projects], format_func=lambda id: projects.get(projects.id == id, {}).get("name", "").values[0])



st.sidebar.divider()



is_filtered_by_pinned = st.sidebar.checkbox("📌 Viktiga")
is_filtered_by_archived = st.sidebar.checkbox("🗑️ Papperskorg")

st.sidebar.divider()

#
# Settings
#

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

with st.sidebar.expander("Settings", expanded=False):
    openai_api_key = st.text_input("OpenAI API key", value=st.secrets["OPENAI_API_KEY"])
    st.session_state["openai_model"] = st.text_input("OpenAI model", value=st.session_state["openai_model"])

client = OpenAI(api_key=openai_api_key)

#
# Main content
#

if is_filtered_by_project and project_id_selected:
    st.title(projects.get(projects.id == project_id_selected, {}).get("name", "").values[0])
elif is_filtered_by_date and date_selected:
    st.title(date_selected.strftime("%Y/%m/%d"))
# elif len(st.session_state.selected_tags) > 0:
#     st.title(" ".join(st.session_state.selected_tags))
else:
    st.title("DagBok")


# Summary

# Sort descending by timestamp
notes = conn.query("SELECT * FROM notes ORDER BY timestamp DESC")

# filter notes
if not notes.empty:
    if is_filtered_by_project and project_id_selected:
        notes = notes[notes.project_id == project_id_selected]
    elif is_filtered_by_date and date_selected:
        notes = notes[notes.date == date_selected.strftime("%Y-%m-%d")]
    else:
        notes = notes[0:0]

    st.session_state.notes = notes.to_dict(orient="records")
else:
    st.session_state.notes = []


# Query and display the data you inserted
if is_filtered_by_date and date_selected:
    messages = conn.query("SELECT * FROM messages WHERE timestamp >= :today AND timestamp < :next", params={"today": date_selected, "next": date_selected + timedelta(days=1)})
else:
    messages = conn.query("SELECT * FROM messages")

# Convert the 'timestamp' column to a datetime type
messages['timestamp'] = pd.to_datetime(messages['timestamp'])

# Populate project by project_id
messages['project'] = messages["project_id"].apply(lambda id: (conn.query("SELECT * FROM projects WHERE id = :id", params={"id": id}).iloc[0].to_dict() if not conn.query("SELECT * FROM projects WHERE id = :id", params={"id": id}).empty else None) if id else None)

if not messages.empty:
    if is_filtered_by_project:
        messages = messages[messages.project.apply(lambda project: project["id"] == project_id_selected if project else False)]
    if is_filtered_by_pinned:
        messages = messages[messages.pinned == True]
    if not is_filtered_by_archived:
        messages = messages[messages.archived == False]

    st.session_state.messages = messages.to_dict(orient="records")
else:
    st.session_state.messages = []

# dates = messages.timestamp.dt.date.unique()

st.session_state.is_project_open = True

if len(st.session_state.notes) > 0:
    if (is_filtered_by_project and project_id_selected) or (is_filtered_by_date and date_selected):
        st.info(st.session_state.notes[0]["content"])
elif not is_filtered_by_date and not is_filtered_by_project:
    st.info("Vad Har Jag Gjort Idag i APL")
    st.info("""
            Välj En Av Alternativen:
            - 📅 Filtera datum
            - 📝 Filtera Projekt
            - 📌 Pin Viktiga Händelser
            - 🗑️ Papperskorg
            
    """)
elif len(st.session_state.messages) == 0:
    st.info("No activities found.")

if len(st.session_state.messages) > 0:
    if is_filtered_by_project and project_id_selected and len(st.session_state.notes) > 0:
        st.session_state.is_project_open = st.checkbox("Reopen to add a memo", False)
        button_generate_summary = st.button("Generate Summary", disabled=not openai_api_key)
    elif is_filtered_by_date and date_selected and date_selected is not date.today():
        button_generate_summary = st.button("Generate Summary", disabled=not openai_api_key)
    else:
        button_generate_summary = False

    if button_generate_summary:
        if is_filtered_by_project and project_id_selected:
            generate_summary(conn, client, st, project_id=project_id_selected, project_name=projects.get(projects.id == project_id_selected, {}).get("name", "").values[0])
        elif is_filtered_by_date and date_selected:
            generate_summary(conn, client, st, date=date_selected)


# Chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["timestamp"]:
            id = message["id"]
            # If date is selected, show only time. Otherwise, show date and time.
            then = message["timestamp"].time() if is_filtered_by_date and date_selected else message["timestamp"]
            then = then.replace(microsecond=0)
            st.markdown(f"`{then}`\t`#{id}`")
        st.markdown(message["content"])

        col_pinned, col_archived = st.columns(2)
        checkbox_pinned = col_pinned.checkbox("📌 ", value=message["pinned"], key=f"pinned-{message['id']}")
        if message["pinned"] != checkbox_pinned:
            update_pinned(conn, message["id"], checkbox_pinned)
        checkbox_archived = col_archived.checkbox("🗑️", value=message["archived"], key=f"archived-{message['id']}")
        if message["archived"] != checkbox_archived:
            update_archived(conn, message["id"], checkbox_archived)

# Chat input
post = ""
if (not is_filtered_by_date or date_selected == date.today()) and st.session_state.is_project_open:
    post = st.chat_input("Skriv här nere")

if post:
    now = datetime.now()

    with st.chat_message("user"):
        st.markdown(f"`{now.strftime('%H:%M:%S')}`")
        st.markdown(post)

        col_pinned, col_archived = st.columns(2)
        checkbox_pinned = col_pinned.checkbox("📌 ", value=False, key="pinned-new-message-id", disabled=True)
        checkbox_archived = col_archived.checkbox("🗑️", value=False, key="archived-new-message-id", disabled=True)

    # project_id = conn.query("SELECT * FROM projects WHERE id = :id", params={"id": project_id_selected}).iloc[0]["id"] if is_filtered_by_project and project_id_selected else ""
    st.session_state.messages.append({"content": post, "timestamp": now, "role": "user", "project_id": project_id_selected, "archived": False, "pinned": False})

    # Insert some data with conn.session
    if is_filtered_by_project and project_id_selected:
        with conn.session as s:
            s.execute(
                "INSERT INTO messages (content, role, project_id, timestamp) VALUES (:message, :role, :project_id, :timestamp);",
                params=dict(message=post, role="user", project_id=int(project_id_selected), timestamp=now)
            )
            s.commit()
    else:
        with conn.session as s:
            s.execute(
                "INSERT INTO messages (content, role, timestamp) VALUES (:message, :role, :timestamp);",
                params=dict(message=post, role="user", timestamp=now)
            )
            s.commit()

if is_filtered_by_project and project_id_selected and len(st.session_state.messages) > 0 and st.session_state.is_project_open:
    button_close_and_generate_summary = st.button("Close and generate Summary", disabled=not openai_api_key)
    if button_close_and_generate_summary:
        if is_filtered_by_project and project_id_selected:
            generate_summary(conn, client, st, project_id=project_id_selected, project_name=projects.get(projects.id == project_id_selected, {}).get("name", "").values[0])
        elif is_filtered_by_date and date_selected:
            generate_summary(conn, client, st, date=date_selected)
