import streamlit as st
import streamlit_authenticator as stauth
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime,date, timedelta
import sqlite3
import yaml
from yaml.loader import SafeLoader

# Load configuration from YAML file
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"]:
    username = st.session_state["name"]
    st.title('Points Game')
    st.text("")

    categories = {
        'Dire Bonjour': {'weight': 1, 'decay': 0.1},
        'Cold Approach': {'weight': 5, 'decay': 0.2},
        'Demander numero': {'weight': 15, 'decay': 0.3}
    }
    db_file = 'points_log.db'

    def init_db():
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS points_log
                          (user TEXT, timestamp TEXT, category TEXT, increment INTEGER)''')
        conn.commit()
        conn.close()

    def record_click(category, increment):
        current_time = datetime.now().isoformat()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO points_log (user, timestamp, category, increment) VALUES (?, ?, ?, ?)',
                       (username, current_time, category, increment))
        conn.commit()
        conn.close()

    def load_data():
        conn = sqlite3.connect(db_file)
        df = pd.read_sql_query(f"SELECT * FROM points_log", conn)
        conn.close()
        return df

    init_db()

    for category, props in categories.items():
        st.write(f"### {category} - {categories[category]['weight']} pts")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"Plus",key=category+str('plus')):
                st.warning("Are you sure you did good?")
                st.button(f"Yes",key='test',on_click=record_click,args=(category,categories[category]['weight']))

    st.write("## Performance Graph")

    # Assuming df is the DataFrame loaded from the SQLite database
    df = load_data()
    if not df.empty:
        # Select categories to display, defaulting to all categories
        #selected_categories = st.multiselect("Select categories to display", list(categories.keys()), default=list(categories.keys()))
        #for now I remove multiseleect
        selected_categories = list(categories.keys())

        one_week_ago = datetime.now() - timedelta(days=date.today().weekday())#datetime.timedelta(days=7)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_week = df[df['timestamp'] >= one_week_ago]

        fig = go.Figure()

        users = df['user'].unique()
        for user in users:
            user_data = df_week[df_week['user'] == user]
            if selected_categories:
                data = user_data[user_data['category'].isin(selected_categories)]
                if not data.empty:
                    summed_data = data.groupby('timestamp')['increment'].sum().cumsum()
                    fig.add_trace(go.Scatter(
                        x=summed_data.index,
                        y=summed_data.values,
                        mode='lines',
                        name=f"{user}"
                    ))

                    # Highlight "Demander numero" events with stars on the plot line
                    if 'Demander numero' in selected_categories:
                        demander_numero_data = user_data[user_data['category'] == 'Demander numero']
                        for timestamp in demander_numero_data['timestamp']:
                            sum_up_to_event = summed_data[timestamp]
                            fig.add_trace(go.Scatter(
                                x=[timestamp],
                                y=[sum_up_to_event],
                                mode='markers',
                                marker=dict(color='red', size=10, symbol='star'),
                                showlegend=False
                                #name=f"{user} - Demander numero event"
                            ))

        fig.update_layout(
            title="Performance Graph",
            xaxis_title="Timestamp",
            yaxis_title="Cumulative Points",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Display static Plotly chart
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})

with open('config.yaml', 'w') as file:
    yaml.dump(config, file, default_flow_style=False)