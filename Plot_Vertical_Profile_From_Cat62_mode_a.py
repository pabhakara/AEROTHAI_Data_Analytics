import psycopg2
import psycopg2.extras
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import (AutoMinorLocator, MultipleLocator)
from matplotlib.dates import DateFormatter
import os
import glob

import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from dash import Dash, html, dcc
import time
import datetime as dt


def none_to_null(etd):
    if etd == 'None':
        x = 'null'
    else:
        x = "'" + etd + "'"
    return x


# conn_postgres_source = psycopg2.connect(user="pongabhaab",
#                                              password="pongabhaab2",
#                                              host="172.16.129.241",
#                                              port="5432",
#                                              database="aerothai_dwh",
#                                              options="-c search_path=dbo,sur_air")

conn_postgres_source = psycopg2.connect(user="postgres",
                                        password="password",
                                        host="localhost",
                                        port="5432",
                                        database="temp",
                                        options="-c search_path=dbo,sur_air")

output_filepath = '/Users/pongabha/Dropbox/Workspace/AEROTHAI Data Analytics/Flight_Proflie_Plots/'
files = glob.glob(f"{output_filepath}*")
for f in files:
    os.remove(f)

year = '2024'
month = '08'
day = '22'

#STAR_list = ['LEBIM','NORTA','EASTE','WILLA','DOLNI']
STAR_list = ['%']

with (conn_postgres_source):
    cursor_postgres_source = conn_postgres_source.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Create an SQL query that selects the list of flights that we want plot
    # from the source PostgreSQL database
    for STAR in STAR_list:
        postgres_sql_text = f"SELECT DISTINCT t.mode_a_code, f.actype, '{STAR}' " \
                            f"FROM sur_air.cat062_{year}{month}{day} t " \
                            f"LEFT JOIN flight_data.flight_{year}{month} f " \
                            f"ON t.flight_id = f.id " \
                            f"WHERE (f.dep LIKE '%' AND f.dest LIKE '%') " \
                            f"AND t.mode_a_code = '3306' " \
                            f"AND app_time < '2024-08-22T08:40:31.000' " \
                            f"AND app_time > '2024-08-22T06:40:31.000' " \
                            f"AND f.flight_key LIKE '%' " \
                            f"AND f.frule LIKE '%'; "
        cursor_postgres_source.execute(postgres_sql_text)
        print(postgres_sql_text)

        record = cursor_postgres_source.fetchall()
        print(record)
        summary_df = pd.DataFrame(record, columns=['mode_a_code', 'actype', 'star'])

    #flight_key_list = list(summary_df['flight_key'])
    mode_a_list = list(summary_df['mode_a_code'])

#print(flight_key_list)

fig = make_subplots(specs=[[{"secondary_y": True}]])

track_duration_list = []
track_distance_list = []

mode_a_code_list = ['3306']
with conn_postgres_source:
    #for flight_key in flight_key_list:
    for mode_a_code in mode_a_code_list:
        print(mode_a_code)
        cursor_postgres_source = conn_postgres_source.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Create an SQL query that selects surveillance targets based on the list of selected flights
        # from the source PostgreSQL database
        postgres_sql_text = f"SELECT t.mode_a_code, t.app_time, t.sector, t.dist_from_last_position, t.baro_alt " \
                            f", t.final_state_selected_alt_dap " \
                            f", t.latitude, t.longitude " \
                            f"FROM sur_air.cat062_{year}{month}{day} t " \
                            f"LEFT JOIN flight_data.flight_{year}{month} f " \
                            f"ON t.flight_id = f.id " \
                            f"LEFT JOIN airac_current.airports a " \
                            f"ON a.airport_identifier = f.dest " \
                            f"WHERE t.mode_a_code = '{mode_a_code}' AND " \
                            f"t.flight_key is NULL AND " \
                            f"t.app_time < '2024-08-22T08:40:31.000' AND " \
                            f"t.app_time > '2024-08-22T06:40:31.000' " \
                            f"ORDER BY t.app_time "
        # f"AND public.ST_WITHIN(t.\"2d_position\",public.ST_Buffer(a.geom,2)) " \

        print(postgres_sql_text)
        cursor_postgres_source.execute(postgres_sql_text)
        record = cursor_postgres_source.fetchall()
        df = pd.DataFrame(record,
                          columns=['mode_a_code', 'app_time', 'sector', 'dist_from_last_position', 'baro_alt',
                                   'final_state_selected_alt_dap', 'latitude', 'longitude'])

        print(df)

        accumulated_distance = 0
        accumulated_distance_list = []

        accumulated_time = 0
        accumulated_time_list = []

        for k in range(len(df)):
            accumulated_distance = accumulated_distance + df['dist_from_last_position'][k]
            accumulated_time = df['app_time'][k] - df['app_time'][0]
            #print(accumulated_distance)
            #print(df['dist_from_last_position'][k])
            accumulated_distance_list.append(accumulated_distance)
            accumulated_time_list.append(accumulated_time)

        df['accumulated_distance'] = pd.DataFrame(accumulated_distance_list, columns=['accumulated_distance'])
        df['accumulated_time'] = pd.DataFrame(accumulated_time_list, columns=['accumulated_time'])

        track_duration_list.append(df.iloc[-1, -1])
        track_distance_list.append(df.iloc[-1, -2])

        print(df)
        #
        # fig = make_subplots(
        #     rows=1, cols=1,
        #     # specs=[[{"type": "scatter"}, {"type": "mapbox"},{"type": "scatter3d"}]])
        #     # specs=[[{"type": "scatter"}, {"type": "mapbox"},{"type": "scatter3d"}]])

        # fig = make_subplots(specs=[[{"secondary_y": True}]])

        #fig = go.Figure()

        # fig.add_trace(go.Line(name=f"{mode_a_code}",
        #                       x=(df["accumulated_time"]),
        #                       y=(df["baro_alt"] * 100)),
        #               secondary_y=False,
        #               )

        fig.add_trace(go.Line(name=f"{mode_a_code}",
                              x=(df["app_time"]),
                              y=(df["baro_alt"] * 100)),
                      secondary_y=False,
                      )

        # fig.add_trace(go.Line(name="FSS Altitude",
        #                       x=df["accumulated_distance"],
        #                       y=df["final_state_selected_alt_dap"]),
        #               secondary_y=False,
        #               )

        # Add figure title
        fig.update_layout(
            title_text=f"Vertical Profile of Flight {mode_a_code}"
            #title_text=f"Vertical Profile"
        )

        # Set x-axis title
        fig.update_xaxes(title_text="Accumulated Distance (NM)")

        # Set y-axes titles
        #fig.update_yaxes(title_text="<b>Measured FL (ft)</b>", secondary_y=False)
        fig.update_yaxes(title_text=f"<b>Altitude (ft)</b>", secondary_y=False)

    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(
                visible=True
            ),
            type="-"
        )
    )

    fig.show()

summary_df['track_duration'] = pd.DataFrame(track_duration_list, columns=['track_duration'])
summary_df['track_distance'] = pd.DataFrame(track_distance_list, columns=['track_distance'])

print(summary_df)
