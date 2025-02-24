import pandas as pd
import numpy as np
import streamlit as st
import psycopg2
import hashlib
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO
import xlsxwriter
import plotly.express as px
import os
import boto3
import uuid


# AWS DynamoDB-Client initialisieren
dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

table_name = "oikos_budgeting"
table = dynamodb.Table(table_name)


# Benutzer und Passwörter aus Umgebungsvariablen lesen
users = {
    "oikos_board": hashlib.sha256(os.getenv("OIKOS_BOARD_PASSWORD").encode()).hexdigest(),
}

user_names = {
    "oikos_board": "board"
}

# CSS für rechtsbündige Buttons
st.markdown("""
    <style>
    .stButton button {
        float: right;
    }
    </style>
    """, unsafe_allow_html=True)


# Haupt-App
def app():
    st.title("Hey oikee!")
    st.subheader(f"Welcome to the oikos budgeting tool.")
    st.write("")
    st.write("")
    with st.expander("Instructions"):
        st.write("Instructions go here")

    st.write("")
    st.header("View registered expenses")

    # Funktion zum Abrufen aller Daten aus DynamoDB
    def get_data():
        try:
            response = table.scan()
            data = response.get("Items", [])
    
            # Falls Tabelle leer ist, gib einen leeren DataFrame zurück
            if not data:
                return pd.DataFrame()
    
            # DynamoDB speichert Zahlen als Dezimal, daher in float konvertieren
            for item in data:
                if 'exact_amount' in item:
                    item['exact_amount'] = float(item['exact_amount']) if item['exact_amount'] else None
                if 'estimated' in item:
                    item['estimated'] = float(item['estimated']) if item['estimated'] else None
                if 'conservative' in item:
                    item['conservative'] = float(item['conservative']) if item['conservative'] else None
                if 'worst_case' in item:
                    item['worst_case'] = float(item['worst_case']) if item['worst_case'] else None
                if 'priority' in item:
                    item['priority'] = int(item['priority']) if item['priority'] else None
    
            df = pd.DataFrame(data)
            return df
    
        except Exception as e:
            st.error(f"Error connecting to DynamoDB: {e}")
            return pd.DataFrame()


    # Funktion zum Abrufen der Farbe basierend auf dem Projektnamen
    def get_color(project_name):
        if project_name == "oikos Conference":
            return "#4386e8"
        elif project_name == "Sustainability Week":
            return "#66ddc1"
        elif project_name == "Action Days":
            return "#e1d9c4"
        elif project_name == "Curriculum Change":
            return "#e681e5"
        elif project_name == "UN-DRESS":
            return "#a3a3a3"
        elif project_name == "ChangeHub":
            return "#f7be6d"
        elif project_name == "oikos Solar":
            return "#7a89f7"
        elif project_name == "oikos Catalyst":
            return "#7fcaf9"
        elif project_name == "Climate Neutral Events":
            return "#3a9953"
        elif project_name == "oikos Consulting":
            return "#b84040"
        elif project_name == "Sustainable Finance":
            return "#fa8128"
        elif project_name == "Oismak":
            return "#bccbdd"
        else:
            return "#FFFFFF"  # Standardfarbe

    # Daten aus der Datenbank abrufen
    df = get_data()

    if df is not None:

        # Radio Buttons für die Sortieroptionen
        sort_option = st.radio(
            "Sort data by:",
            ("ID", "Project", "Priority", "Date"),
            index=0  # Standardmäßig "ID" auswählen
        )

        # Sortierung basierend auf der Benutzerwahl
        if sort_option == "ID":
            df = df.sort_values(by="id")
        elif sort_option == "Project":
            df = df.assign(project_lower=df['project'].str.lower())  # Neue Spalte mit kleinbuchstabigen Projektnamen hinzufügen
            df = df.sort_values(by="project_lower").drop(columns="project_lower")  # Sortiere nach der neuen Spalte und entferne sie danach
        elif sort_option == "Priority":
            df = df.sort_values(by="priority", ascending=True)
        elif sort_option == "Date":
            df = df.sort_values(by="expense_date")

        st.write("")


        # Checkboxen für die Filterung nach Projekten
        st.write("Select Projects to Display:")

        # Ermitteln der eindeutigen Projekte
        unique_projects = df['project'].unique()

        # Anzahl der Spalten definieren
        cols = st.columns(3, vertical_alignment="top")  # Erstellen der Spalten

        # Liste für ausgewählte Projekte
        selected_projects = []

        # Iteriere über alle Projekte und ordne sie den Spalten zu
        for index, project in enumerate(unique_projects):
            col = cols[index % 3]  # Füge Projekte der entsprechenden Spalte hinzu
            if col.checkbox(project, value=True):
                selected_projects.append(project)

        # Filtere den DataFrame basierend auf den ausgewählten Projekten
        if selected_projects:
            df = df[df['project'].isin(selected_projects)]

        st.write("")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Checkboxen für die Filterung nach 'expense_date'
            st.write("Filter by Expense Date:")

            # Filteroptionen: 'No Date', 'Unknown', 'Date'
            filter_no_date = st.checkbox("No Date", value=True)
            filter_unknown = st.checkbox("Unknown", value=True)
            filter_with_date = st.checkbox("Date", value=True)

            # Filterlogik für 'expense_date'
            if filter_no_date or filter_unknown or filter_with_date:
                date_conditions = []
                
                if filter_no_date:
                    # Filter für None in 'expense_date'
                    date_conditions.append(df['expense_date'].isna())
                
                if filter_unknown:
                    # Filter für 'unknown' in 'expense_date'
                    date_conditions.append(df['expense_date'] == 'unknown')
                
                if filter_with_date:
                    # Filter für gültige Daten (nicht None und nicht 'unknown')
                    date_conditions.append((df['expense_date'].notna()) & (df['expense_date'] != 'unknown'))
                
                # Kombiniere alle Bedingungen mit OR (any)
                df = df[np.logical_or.reduce(date_conditions)]


        with col2:
            # Checkboxen für die Filterung nach Exact und Estimated
            st.write("Select Exact or Estimated Amounts to Display:")

            # Erstelle die Checkboxen für Exact und Estimated
            show_exact = st.checkbox("Exact", value=True)
            show_estimated = st.checkbox("Estimated", value=True)

            # Filtere den DataFrame basierend auf den Checkboxen
            if show_exact and not show_estimated:
                # Zeige nur Einträge mit einem genauen Betrag (nicht leer)
                df = df[df['exact_amount'].notna()]
            elif show_estimated and not show_exact:
                # Zeige nur Einträge, bei denen der genaue Betrag leer ist (also geschätzt)
                df = df[df['exact_amount'].isna()]
            elif not show_exact and not show_estimated:
                # Falls beide Checkboxen deaktiviert sind, wird kein Eintrag angezeigt
                df = df[df['exact_amount'] == None]
            # Wenn beide aktiviert sind, wird der gesamte DataFrame angezeigt (kein Filter)




        with col3:
            # Checkboxen für die Filterung nach Priorität
            st.write("Select Priorities to Display:")

            # Liste für die Prioritäten-Checkboxen
            selected_priorities = []

            # Erstelle die Checkboxen für die Prioritäten 1 bis 5
            for priority in range(1, 6):
                if st.checkbox(f"Priority {priority}", value=True):
                    selected_priorities.append(priority)

            # Filtere den DataFrame basierend auf den ausgewählten Prioritäten
            if selected_priorities:
                df = df[df['priority'].isin(selected_priorities)]



        # DataFrame anzeigen
        st.write("")
        st.dataframe(df.set_index('id'), height = 250)

    tab1, tab2, tab3 = st.tabs(["Overview", "Insights", "Edit"])

    with tab1:
        # Generiere die Container basierend auf dem sortierten DataFrame
        st.write("")

        # Funktion zum Aktualisieren des Status eines Eintrags
        def update_status(expense_id, new_status):
            try:
                table.update_item(
                    Key={"id": str(expense_id)},  # ID muss String sein
                    UpdateExpression="SET #s = :s",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":s": new_status},
                    ReturnValues="UPDATED_NEW"
                )
            except Exception as error:
                st.error(f"Error updating expense status: {error}")


        def display_expenses_by_status(df, status, section_title):
            #CSS für keinen Rand bei Buttons
            st.markdown("""
                <style>
                .stButton button {
                    border: none;
                    background-color: transparent;
                    box-shadow: none;
                    padding: 0;
                }
                </style>
            """, unsafe_allow_html=True)

            # Filtere den DataFrame nach dem Status
            df_filtered = df[df['status'] == status]

            if not df_filtered.empty:
                st.subheader(section_title)
                for i in range(0, len(df_filtered), 3):
                    cols = st.columns(3)
                    for j, col in enumerate(cols):
                        if i + j < len(df_filtered):
                            entry = df_filtered.iloc[i + j]
                            color = get_color(entry['project'])

                            with col:
                                # Container-Inhalt mit den Details der Expense
                                container_content = f"""
                                <div style='background-color: {color}; padding: 15px; border-radius: 10px; margin-bottom: 10px;'>
                                    <p><strong>ID: </strong>{entry['id']}</p>
                                    <p><strong>Project: </strong>{entry['project']}</p>
                                    <h4>{entry['title']}</h4>
                                    <p>{entry['description']}</p>
                                    <p><strong>Date: </strong>{entry['expense_date']}</p>
                                    <p><strong>Amount:</strong> CHF {entry['exact_amount'] if entry['exact_amount'] else f"{entry['estimated']} / {entry['conservative']} / {entry['worst_case']}"}</p>
                                    <p><strong>Priority:</strong> {entry['priority']}</p>
                                    <p><strong>Status:</strong> {entry['status']}</p>
                                </div>
                                """
                                col.markdown(container_content, unsafe_allow_html=True)

                                # Buttons in einer horizontalen Linie innerhalb des Containers anzeigen
                                with col.container():
                                    col1, col2, col3 = st.columns([1.7, 1, 1])  # Zwei Spalten für die Buttons
                                    if entry['status'] == 'not assigned':
                                        with col1:
                                            if st.button("✅", key=f"approve_{entry['id']}"):
                                                update_status(entry['id'], 'approved')
                                                st.rerun()
                                        with col2:
                                            if st.button("❌", key=f"reject_{entry['id']}"):
                                                update_status(entry['id'], 'rejected')
                                                st.rerun()

                                    elif entry['status'] == 'approved':
                                        with col1:
                                            if st.button("⏹️", key=f"not_assigned_{entry['id']}"):
                                                update_status(entry['id'], 'not assigned')
                                                st.rerun()
                                        with col2:
                                            if st.button("❌", key=f"reject_{entry['id']}"):
                                                update_status(entry['id'], 'rejected')
                                                st.rerun()

                                    elif entry['status'] == 'rejected':
                                        with col1:
                                            if st.button("⏹️", key=f"not_assigned_{entry['id']}"):
                                                update_status(entry['id'], 'not assigned')
                                                st.rerun()
                                        with col2:
                                            if st.button("✅", key=f"approve_{entry['id']}"):
                                                update_status(entry['id'], 'approved')
                                                st.rerun()


                    st.write("")

        # Zeige die Einträge in den jeweiligen Sektionen
        display_expenses_by_status(df, 'not assigned', 'Not Assigned Expenses')
        display_expenses_by_status(df, 'approved', 'Approved Expenses')
        display_expenses_by_status(df, 'rejected', 'Rejected Expenses')



        st.write("")
        st.write("")

        def create_excel_with_overview(df):
            # Excel-Datei in den Speicher schreiben
            output = BytesIO()

            # Erstellen eines Pandas-Excel-Writers mit XlsxWriter
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Übersichtsliste für das Overview-Tabellenblatt
                overview_data = []

                # Finde alle eindeutigen Projekte
                projects = df['project'].unique()

                # Berechne die Übersichtsdaten und speichere sie für das Overview-Tabellenblatt
                for project in projects:
                    # Filtere die Daten für das Projekt
                    df_project = df[df['project'] == project]

                    # Schreibe den gefilterten DataFrame auf ein separates Tabellenblatt
                    df_project.to_excel(writer, sheet_name=project, index=False)

                    # Berechne die Übersichtsdaten für das Projekt
                    total_entries = len(df_project)

                    # Zähle Einträge mit exact_amount, die größer als 0 sind
                    exact_entries = (df_project['exact_amount'] > 0).sum()

                    # Summiere die Werte der exact_amount
                    exact_sum = df_project['exact_amount'].sum(skipna=True)

                    # Zähle Einträge, bei denen exact_amount NaN oder 0 ist und estimated Werte vorhanden sind
                    estimated_entries = ((df_project['exact_amount'].isna()) | (df_project['exact_amount'] == 0)).sum()

                    # Summiere die Werte der estimated Spalte
                    estimated_sum = df_project['estimated'].sum(skipna=True)

                    # Summiere die Werte der konservativen und worst_case Schätzungen
                    conservative_sum = df_project['conservative'].sum(skipna=True)
                    worst_case_sum = df_project['worst_case'].sum(skipna=True)

                    # Füge die Daten zur Übersicht hinzu
                    overview_data.append({
                        'Projekt': project,
                        'Registered Expenses': total_entries,
                        'Exact Expenses': exact_entries,
                        'Total Exact Expenses': exact_sum,
                        'Estimated Expenses': estimated_entries,
                        'Total Estimated': estimated_sum,
                        'Total Conservatively Estimated': conservative_sum,
                        'Total Worst Case': worst_case_sum
                    })

                # Erstelle das Overview DataFrame
                overview_df = pd.DataFrame(overview_data)

                # Schreibe das Overview-Tabellenblatt als erstes Blatt
                overview_df.to_excel(writer, sheet_name='Overview', index=False)

                # Schreibe jedes Projekt auf ein eigenes Tabellenblatt
                for project in projects:
                    df_project = df[df['project'] == project]
                    df_project.to_excel(writer, sheet_name=project, index=False)

                # Hole den XlsxWriter-Objekt für weitere Formatierungen
                workbook = writer.book
                overview_worksheet = writer.sheets['Overview']

                # Überschrift formatieren
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })

                # Wende Formatierung auf die erste Zeile des Overview-Blattes an
                for col_num, value in enumerate(overview_df.columns.values):
                    overview_worksheet.write(0, col_num, value, header_format)

            # Zurückspulen des Speichers
            output.seek(0)

            return output


        # Streamlit Button zum Herunterladen der Excel-Datei
        excel_file = create_excel_with_overview(df)

        # Download-Button für die formatierte Excel-Datei
        st.download_button(
            label="Download Excel",
            data=excel_file,
            file_name='oikos_budgeting_projects.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


    with tab2:
        # Ersetze NaN-Werte in den relevanten Spalten durch 0
        df['exact_amount'] = pd.to_numeric(df['exact_amount'], errors='coerce').fillna(0)
        df['estimated'] = pd.to_numeric(df['estimated'], errors='coerce').fillna(0)
        df['conservative'] = pd.to_numeric(df['conservative'], errors='coerce').fillna(0)
        df['worst_case'] = pd.to_numeric(df['worst_case'], errors='coerce').fillna(0)

        # Gruppiere den DataFrame nach Projekt und summiere die Spalten
        grouped_df = df.groupby('project').agg({
            'exact_amount': 'sum',
            'estimated': 'sum',
            'conservative': 'sum',
            'worst_case': 'sum'
        }).reset_index()

        # Berechne die Gesamtsummen NACH der Gruppierung
        total_exact_amount = grouped_df['exact_amount'].sum()
        total_estimated = grouped_df['estimated'].sum()
        total_conservative = grouped_df['conservative'].sum()
        total_worst_case = grouped_df['worst_case'].sum()

        # Sortiere den DataFrame nach der Worst-Case-Summe in absteigender Reihenfolge
        grouped_df['total_sum'] = grouped_df['exact_amount'] + grouped_df['worst_case']
        grouped_df = grouped_df.sort_values(by='total_sum', ascending=True)

        st.subheader("Expenses per project")
        # Füge den Toggle-Button in einem rechtsbündigen Container hinzu
        show_sum = st.toggle("Show Total Expenses", value=False)


        # Initialisiere das Diagramm
        fig = go.Figure()

        # Durchlaufe jedes Projekt und füge die Balken hinzu
        for project in grouped_df['project']:
            sum_exact_amount = grouped_df.loc[grouped_df['project'] == project, 'exact_amount'].values[0]
            sum_estimated = grouped_df.loc[grouped_df['project'] == project, 'estimated'].values[0]
            sum_conservative = grouped_df.loc[grouped_df['project'] == project, 'conservative'].values[0]
            sum_worst_case = grouped_df.loc[grouped_df['project'] == project, 'worst_case'].values[0]

            # Füge den Balken für das Worst-Case-Szenario hinzu (ganz hinten)
            fig.add_trace(go.Bar(
                x=[sum_exact_amount + sum_worst_case],
                y=[project],  # Projektnamen als Beschriftung verwenden
                orientation='h',
                name=f'{project} - Worst Case',
                marker=dict(color='#FFB3B3'),  # Rot
                showlegend=False,
                hoverinfo="x"
            ))

            # Füge den Balken für das Conservative-Szenario hinzu (darüber)
            fig.add_trace(go.Bar(
                x=[sum_exact_amount + sum_conservative],
                y=[project],
                orientation='h',
                name=f'{project} - Conservative',
                marker=dict(color='#FFD1A9'),  # Orange
                showlegend=False,
                hoverinfo="x"
            ))

            # Füge den Balken für das Estimated-Szenario hinzu (weiter vorne)
            fig.add_trace(go.Bar(
                x=[sum_exact_amount + sum_estimated],
                y=[project],
                orientation='h',
                name=f'{project} - Estimated',
                marker=dict(color='#FDE780'),  # Gelb
                showlegend=False,
                hoverinfo="x"
            ))

            # Füge den Balken für den Exact Amount hinzu (ganz vorne)
            fig.add_trace(go.Bar(
                x=[sum_exact_amount],
                y=[project],
                orientation='h',
                name=f'{project} - Exact',
                marker=dict(color='#AAD4F4'),  # Blau
                showlegend=False,
                hoverinfo="x"
            ))

        # Füge den zusätzlichen Balken für die Gesamtsumme hinzu, wenn der Toggle aktiviert ist
        if show_sum:
            fig.add_trace(go.Bar(
                x=[total_exact_amount + total_worst_case],
                y=["Total Expenses"],
                orientation='h',
                name='Total - Worst Case',
                marker=dict(color='#FFB3B3'),  # Rot
                showlegend=True,
                hoverinfo="x"
            ))

            fig.add_trace(go.Bar(
                x=[total_exact_amount + total_conservative],
                y=["Total Expenses"],
                orientation='h',
                name='Total - Conservative',
                marker=dict(color='#FFD1A9'),  # Orange
                showlegend=True,
                hoverinfo="x"
            ))

            fig.add_trace(go.Bar(
                x=[total_exact_amount + total_estimated],
                y=["Total Expenses"],
                orientation='h',
                name='Total - Estimated',
                marker=dict(color='#FDE780'),  # Gelb
                showlegend=True,
                hoverinfo="x"
            ))

            fig.add_trace(go.Bar(
                x=[total_exact_amount],
                y=["Total Expenses"],
                orientation='h',
                name='Total - Exact',
                marker=dict(color='#AAD4F4'),  # Blau
                showlegend=True,
                hoverinfo="x"
            ))

        # Layout des Diagramms anpassen
        fig.update_layout(
            xaxis_title="CHF",
            yaxis=dict(showticklabels=True),
            barmode='overlay',  # Balken überlappen sich
            height=600,
            margin=dict(l=10, r=10, t=10, b=10)  # Reduziert die Ränder
        )


        # Zeige das Diagramm in Streamlit an
        st.plotly_chart(fig)





        # Erstellen der "_complete"-Spalten durch Addition der entsprechenden Spalten
        df['estimated_complete'] = df['exact_amount'].fillna(0) + df['estimated'].fillna(0)
        df['conservative_complete'] = df['exact_amount'].fillna(0) + df['conservative'].fillna(0)
        df['worst_case_complete'] = df['exact_amount'].fillna(0) + df['worst_case'].fillna(0)

    
        st.write("")
        st.write("")


        col1, col2 = st.columns(2)


        with col1:
            # pie chart exact amount
            # Schritt 1: Aggregiere die exakten Werte nach Projekt
            project_totals = df.groupby('project')['exact_amount'].sum().reset_index()

            # Schritt 2: Sortiere die Projekte nach aggregierten Werten absteigend und berechne die Prozentsätze
            total_exact_amount = project_totals['exact_amount'].sum()
            project_totals['percentage'] = (project_totals['exact_amount'] / total_exact_amount) * 100
            project_totals = project_totals.sort_values(by='exact_amount', ascending=False)

            # Schritt 3: Ranke die Projekte basierend auf den aggregierten exakten Werten
            project_totals['rank'] = project_totals['exact_amount'].rank(ascending=False, method='dense').astype(int)

            # Schritt 4: Füge den einzelnen Einträgen im DataFrame das Ranking ihres Projekts hinzu
            # Hier stellen wir sicher, dass 'rank' korrekt hinzugefügt wird.
            df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project', how='left')

            # Schritt 5: Sortiere die Einträge nach dem Rang ihres Projekts (höchstes Ranking zuerst)
            df_ordered = df_ordered.sort_values(by=['rank', 'exact_amount'], ascending=[True, False])

            # Schritt 6: Erstelle das Piechart basierend auf der Reihenfolge der Projekte
            fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

            # Pie chart für exact_amount, basierend auf dem Ranking der Projekte
            wedges, texts, autotexts = ax_pie.pie(
                df_ordered['exact_amount'],
                labels=None,  # Keine Labels direkt an den Wedges
                colors=[get_color(project) for project in df_ordered['project']],  # Verwende die get_color Funktion
                autopct=lambda p: f'{p:.1f}%' if p > 0 else '',  # Zeige Prozentwerte für jedes Segment an
                startangle=90,
                counterclock=False,
                wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}  # Dünne Linie trennt die Wedges
            )

            # Formatiere die Prozentwerte in den Segmenten (automatisch hinzugefügt)
            for autotext in autotexts:
                autotext.set_color('black')  # Setze die Textfarbe auf Schwarz
                autotext.set_fontsize(10)    # Setze die Schriftgröße für bessere Lesbarkeit

            # Definiere die Labels für die Legende (Projektname und Prozente)
            legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

            # Erstellen der Legende basierend auf dem Projekt-Ranking
            handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

            # Platzierung der Legende
            ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')

            # Titel und Ausrichtung des Kuchendiagramms
            ax_pie.set_title("Share of Exact Expenses by Project", fontsize=20, fontweight='bold')
            ax_pie.axis('equal')  # Sicherstellen, dass es ein Kreis bleibt

            # Zeige das Kuchendiagramm in Streamlit an
            st.pyplot(fig_pie)



        
        with col2:
            # pie chart estimated amount
            # Schritt 1: Aggregiere die geschätzten Werte nach Projekt
            project_totals = df.groupby('project')['estimated_complete'].sum().reset_index()

            # Schritt 2: Sortiere die Projekte nach aggregierten Werten absteigend und berechne die Prozentsätze
            total_estimated = project_totals['estimated_complete'].sum()
            project_totals['percentage'] = (project_totals['estimated_complete'] / total_estimated) * 100
            project_totals = project_totals.sort_values(by='estimated_complete', ascending=False)

            # Schritt 3: Ranke die Projekte basierend auf den aggregierten geschätzten Werten
            project_totals['rank'] = project_totals['estimated_complete'].rank(ascending=False, method='dense').astype(int)

            # Schritt 4: Sortiere den originalen DataFrame basierend auf der Reihenfolge der Projekte im 'project_totals'
            df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project')
            df_ordered = df_ordered.sort_values(by=['rank', 'estimated_complete'], ascending=[True, False])

            # Schritt 5: Erstelle das Piechart basierend auf der Reihenfolge der Projekte
            fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

            # Pie chart für estimated, basierend auf dem Ranking der Projekte
            wedges, texts, autotexts = ax_pie.pie(
                df_ordered['estimated_complete'],
                labels=None,  # Keine Labels direkt an den Wedges
                colors=[get_color(project) for project in df_ordered['project']],  # Verwende die get_color Funktion
                autopct=lambda p: f'{p:.1f}%' if p > 0 else '',  # Zeige Prozentwerte für jedes Segment an
                startangle=90,
                counterclock=False,
                wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}  # Dünne Linie trennt die Wedges
            )

            # Formatiere die Prozentwerte in den Segmenten (automatisch hinzugefügt)
            for autotext in autotexts:
                autotext.set_color('black')  # Setze die Textfarbe auf Schwarz
                autotext.set_fontsize(10)    # Setze die Schriftgröße für bessere Lesbarkeit

            # Definiere die Labels für die Legende (Projektname und Prozente)
            legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

            # Erstellen der Legende basierend auf dem Projekt-Ranking
            handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

            # Platzierung der Legende
            ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')

            # Titel und Ausrichtung des Kuchendiagramms
            ax_pie.set_title("Share of Expenses by Project; scenario: estimated", fontsize=20, fontweight='bold')
            ax_pie.axis('equal')  # Sicherstellen, dass es ein Kreis bleibt

            # Zeige das Kuchendiagramm in Streamlit an
            st.pyplot(fig_pie)



        col1, col2 = st.columns(2)
        with col1:
            # pie chart conservative amount
            # Schritt 1: Aggregiere die konservativen Werte nach Projekt
            project_totals = df.groupby('project')['conservative_complete'].sum().reset_index()

            # Schritt 2: Sortiere die Projekte nach aggregierten Werten absteigend und berechne die Prozentsätze
            total_conservative = project_totals['conservative_complete'].sum()
            project_totals['percentage'] = (project_totals['conservative_complete'] / total_conservative) * 100
            project_totals = project_totals.sort_values(by='conservative_complete', ascending=False)

            # Schritt 3: Ranke die Projekte basierend auf den aggregierten konservativen Werten
            project_totals['rank'] = project_totals['conservative_complete'].rank(ascending=False, method='dense').astype(int)

            # Schritt 4: Füge den einzelnen Einträgen im DataFrame das Ranking ihres Projekts hinzu
            # Hier stellen wir sicher, dass 'rank' korrekt hinzugefügt wird.
            df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project', how='left')

            # Schritt 5: Sortiere die Einträge nach dem Rang ihres Projekts (höchstes Ranking zuerst)
            df_ordered = df_ordered.sort_values(by=['rank', 'conservative_complete'], ascending=[True, False])

            # Schritt 6: Erstelle das Piechart basierend auf der Reihenfolge der Projekte
            fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

            # Pie chart für conservative, basierend auf dem Ranking der Projekte
            wedges, texts, autotexts = ax_pie.pie(
                df_ordered['conservative_complete'],
                labels=None,  # Keine Labels direkt an den Wedges
                colors=[get_color(project) for project in df_ordered['project']],  # Verwende die get_color Funktion
                autopct=lambda p: f'{p:.1f}%' if p > 0 else '',  # Zeige Prozentwerte für jedes Segment an
                startangle=90,
                counterclock=False,
                wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}  # Dünne Linie trennt die Wedges
            )

            # Formatiere die Prozentwerte in den Segmenten (automatisch hinzugefügt)
            for autotext in autotexts:
                autotext.set_color('black')  # Setze die Textfarbe auf Schwarz
                autotext.set_fontsize(10)    # Setze die Schriftgröße für bessere Lesbarkeit

            # Definiere die Labels für die Legende (Projektname und Prozente)
            legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

            # Erstellen der Legende basierend auf dem Projekt-Ranking
            handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

            # Platzierung der Legende
            ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')

            # Titel und Ausrichtung des Kuchendiagramms
            ax_pie.set_title("Share of Expenses by Project; scenario: conservative", fontsize=20, fontweight='bold')
            ax_pie.axis('equal')  # Sicherstellen, dass es ein Kreis bleibt

            # Zeige das Kuchendiagramm in Streamlit an
            st.pyplot(fig_pie)



        with col2:
            # pie chart worst case amount
            # Schritt 1: Aggregiere die worst_case-Werte nach Projekt
            project_totals = df.groupby('project')['worst_case_complete'].sum().reset_index()

            # Schritt 2: Sortiere die Projekte nach aggregierten Werten absteigend und berechne die Prozentsätze
            total_worst_case = project_totals['worst_case_complete'].sum()
            project_totals['percentage'] = (project_totals['worst_case_complete'] / total_worst_case) * 100
            project_totals = project_totals.sort_values(by='worst_case_complete', ascending=False)

            # Schritt 3: Ranke die Projekte basierend auf den aggregierten worst_case-Werten
            project_totals['rank'] = project_totals['worst_case_complete'].rank(ascending=False, method='dense').astype(int)

            # Schritt 4: Füge den einzelnen Einträgen im DataFrame das Ranking ihres Projekts hinzu
            # Hier stellen wir sicher, dass 'rank' korrekt hinzugefügt wird.
            df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project', how='left')

            # Schritt 5: Sortiere die Einträge nach dem Rang ihres Projekts (höchstes Ranking zuerst)
            df_ordered = df_ordered.sort_values(by=['rank', 'worst_case_complete'], ascending=[True, False])

            # Schritt 6: Erstelle das Piechart basierend auf der Reihenfolge der Projekte
            fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

            # Pie chart für worst_case, basierend auf dem Ranking der Projekte
            wedges, texts, autotexts = ax_pie.pie(
                df_ordered['worst_case_complete'],
                labels=None,  # Keine Labels direkt an den Wedges
                colors=[get_color(project) for project in df_ordered['project']],  # Verwende die get_color Funktion
                autopct=lambda p: f'{p:.1f}%' if p > 0 else '',  # Zeige Prozentwerte für jedes Segment an
                startangle=90,
                counterclock=False,
                wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}  # Dünne Linie trennt die Wedges
            )

            # Formatiere die Prozentwerte in den Segmenten (automatisch hinzugefügt)
            for autotext in autotexts:
                autotext.set_color('black')  # Setze die Textfarbe auf Schwarz
                autotext.set_fontsize(10)    # Setze die Schriftgröße für bessere Lesbarkeit

            # Definiere die Labels für die Legende (Projektname und Prozente)
            legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

            # Erstellen der Legende basierend auf dem Projekt-Ranking
            handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

            # Platzierung der Legende
            ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')

            # Titel und Ausrichtung des Kuchendiagramms
            ax_pie.set_title("Share of Expenses by Project; scenario: worst case", fontsize=20, fontweight='bold')
            ax_pie.axis('equal')  # Sicherstellen, dass es ein Kreis bleibt

            # Zeige das Kuchendiagramm in Streamlit an
            st.pyplot(fig_pie)






        # col1, col2 = st.columns(2)

        # with col1:
        #     # pie chart exact amount
        #     # Schritt 1: Aggregiere die exakten Werte nach Projekt
        #     project_totals = df.groupby('project')['exact_amount'].sum().reset_index()

        #     # Schritt 2: Sortiere die Projekte nach aggregierten Werten absteigend und berechne die Prozentsätze
        #     total_exact_amount = project_totals['exact_amount'].sum()
        #     project_totals['percentage'] = (project_totals['exact_amount'] / total_exact_amount) * 100
        #     project_totals = project_totals.sort_values(by='exact_amount', ascending=False)

        #     # Schritt 3: Ranke die Projekte basierend auf den aggregierten exakten Werten
        #     project_totals['rank'] = project_totals['exact_amount'].rank(ascending=False, method='dense').astype(int)

        #     # Schritt 4: Füge den einzelnen Einträgen im DataFrame das Ranking ihres Projekts hinzu
        #     df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project', how='left')

        #     # Schritt 5: Sortiere die Einträge nach dem Rang ihres Projekts (höchstes Ranking zuerst)
        #     df_ordered = df_ordered.sort_values(by=['rank', 'exact_amount'], ascending=[True, False])

        #     # Schritt 6: Erstelle das Piechart basierend auf der Reihenfolge der Projekte
        #     fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

        #     # Pie chart für exact_amount, basierend auf den einzelnen Ausgaben
        #     wedges, texts, autotexts = ax_pie.pie(
        #         df_ordered['exact_amount'],
        #         labels=None,
        #         colors=[get_color(project) for project in df_ordered['project']],
        #         autopct=lambda p: f'{p:.1f}%' if p > 0 else '',
        #         startangle=90,
        #         counterclock=False,
        #         wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}
        #     )

        #     for autotext in autotexts:
        #         autotext.set_color('black')
        #         autotext.set_fontsize(10)

        #     # Definiere die Labels für die Legende (Projektname und Prozente)
        #     legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

        #     handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

        #     ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')
        #     ax_pie.set_title("Exact Expenses by Project", fontsize=20, fontweight='bold')
        #     ax_pie.axis('equal')

        #     st.pyplot(fig_pie)

        # with col2:
        #     # pie chart estimated amount (includes exact amounts)
        #     # Schritt 1: Aggregiere die geschätzten Werte nach Projekt
        #     project_totals = df.groupby('project')['estimated'].sum().reset_index()

        #     # Addiere die exact amounts zu den geschätzten Werten pro Eintrag
        #     df['total_estimated'] = df['exact_amount'] + df['estimated']

        #     # Schritt 2: Berechne die aggregierten Werte für die Legende
        #     total_estimated_amount = project_totals['estimated'].sum() + df['exact_amount'].sum()
        #     project_totals['percentage'] = (project_totals['estimated'] / total_estimated_amount) * 100
        #     project_totals = project_totals.sort_values(by='estimated', ascending=False)

        #     # Schritt 3: Ranke die Projekte basierend auf den aggregierten geschätzten Werten
        #     project_totals['rank'] = project_totals['estimated'].rank(ascending=False, method='dense').astype(int)

        #     # Schritt 4: Sortiere den originalen DataFrame basierend auf der Reihenfolge der Projekte im 'project_totals'
        #     df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project', how='left')
        #     df_ordered = df_ordered.sort_values(by=['rank', 'total_estimated'], ascending=[True, False])

        #     # Schritt 5: Erstelle das Piechart basierend auf der Reihenfolge der Projekte
        #     fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

        #     # Pie chart für estimated, basierend auf den einzelnen Einträgen
        #     wedges, texts, autotexts = ax_pie.pie(
        #         df_ordered['total_estimated'],
        #         labels=None,
        #         colors=[get_color(project) for project in df_ordered['project']],
        #         autopct=lambda p: f'{p:.1f}%' if p > 0 else '',
        #         startangle=90,
        #         counterclock=False,
        #         wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}
        #     )

        #     for autotext in autotexts:
        #         autotext.set_color('black')
        #         autotext.set_fontsize(10)

        #     # Definiere die Labels für die Legende (Projektname und Prozente)
        #     legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

        #     handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

        #     ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')
        #     ax_pie.set_title("Estimated Expenses by Project", fontsize=20, fontweight='bold')
        #     ax_pie.axis('equal')

        #     st.pyplot(fig_pie)


        # with col1:
        #     # pie chart conservative amount (includes exact amounts)
        #     project_totals = df.groupby('project')['conservative'].sum().reset_index()

        #     df['total_conservative'] = df['exact_amount'] + df['conservative']

        #     total_conservative_amount = project_totals['conservative'].sum() + df['exact_amount'].sum()
        #     project_totals['percentage'] = (project_totals['conservative'] / total_conservative_amount) * 100
        #     project_totals = project_totals.sort_values(by='conservative', ascending=False)

        #     project_totals['rank'] = project_totals['conservative'].rank(ascending=False, method='dense').astype(int)

        #     df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project', how='left')
        #     df_ordered = df_ordered.sort_values(by=['rank', 'total_conservative'], ascending=[True, False])

        #     fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

        #     wedges, texts, autotexts = ax_pie.pie(
        #         df_ordered['total_conservative'],
        #         labels=None,
        #         colors=[get_color(project) for project in df_ordered['project']],
        #         autopct=lambda p: f'{p:.1f}%' if p > 0 else '',
        #         startangle=90,
        #         counterclock=False,
        #         wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}
        #     )

        #     for autotext in autotexts:
        #         autotext.set_color('black')
        #         autotext.set_fontsize(10)

        #     legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

        #     handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

        #     ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')
        #     ax_pie.set_title("Conservative Expenses by Project", fontsize=20, fontweight='bold')
        #     ax_pie.axis('equal')

        #     st.pyplot(fig_pie)


        # with col2:
        #     # pie chart worst case amount (includes exact amounts)
        #     project_totals = df.groupby('project')['worst_case'].sum().reset_index()

        #     df['total_worst_case'] = df['exact_amount'] + df['worst_case']

        #     total_worst_case_amount = project_totals['worst_case'].sum() + df['exact_amount'].sum()
        #     project_totals['percentage'] = (project_totals['worst_case'] / total_worst_case_amount) * 100
        #     project_totals = project_totals.sort_values(by='worst_case', ascending=False)

        #     project_totals['rank'] = project_totals['worst_case'].rank(ascending=False, method='dense').astype(int)

        #     df_ordered = pd.merge(df, project_totals[['project', 'rank']], on='project', how='left')
        #     df_ordered = df_ordered.sort_values(by=['rank', 'total_worst_case'], ascending=[True, False])

        #     fig_pie, ax_pie = plt.subplots(figsize=(10, 10))

        #     wedges, texts, autotexts = ax_pie.pie(
        #         df_ordered['total_worst_case'],
        #         labels=None,
        #         colors=[get_color(project) for project in df_ordered['project']],
        #         autopct=lambda p: f'{p:.1f}%' if p > 0 else '',
        #         startangle=90,
        #         counterclock=False,
        #         wedgeprops={'edgecolor': 'grey', 'linewidth': 0.5}
        #     )

        #     for autotext in autotexts:
        #         autotext.set_color('black')
        #         autotext.set_fontsize(10)

        #     legend_labels = [f"{row['project']}: {row['percentage']:.1f}%" for i, row in project_totals.iterrows()]

        #     handles = [mpatches.Patch(color=get_color(project), label=legend_labels[i]) for i, project in enumerate(project_totals['project'])]

        #     ax_pie.legend(handles, legend_labels, title="Projects", loc="upper right", frameon=True, fancybox=True, framealpha=1, facecolor='white')
        #     ax_pie.set_title("Worst Case Expenses by Project", fontsize=20, fontweight='bold')
        #     ax_pie.axis('equal')

        #     st.pyplot(fig_pie)





        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")    



        # Schritt 1: Erstelle eine vereinfachte Version des DataFrames für den Bubble Chart
        bubble_df = df[['project', 'exact_amount', 'estimated', 'conservative', 'worst_case', 'priority']]

        # Schritt 2: Berechne den Durchschnitt der Schätzungen pro Projekt (als Blasengröße)
        bubble_df['average_cost'] = bubble_df[['exact_amount', 'estimated', 'conservative', 'worst_case']].mean(axis=1)

        # Schritt 3: Aggregiere den DataFrame nach Projekt (falls es mehrere Einträge pro Projekt gibt)
        bubble_df = bubble_df.groupby('project').agg({
            'priority': 'mean',  # Falls Priorität mehrmals vergeben ist, nimm den Durchschnitt
            'worst_case': 'sum',  # Worst-Case für das Risiko auf der Y-Achse
            'average_cost': 'sum',  # Durchschnittliche Kosten für die Blasengröße
            'exact_amount': 'sum',  # Exakte Ausgaben für die X-Achse
            'estimated': 'sum'  # Optional für spätere Verwendung
        }).reset_index()

        # Schritt 4: Erstelle den Bubble Chart mit Plotly Express
        fig = px.scatter(
            bubble_df,
            x='priority',  # X-Achse: Priorität des Projekts
            y='worst_case',  # Y-Achse: Risiko (Worst-Case)
            size='average_cost',  # Größe der Blasen: Durchschnittliche Kosten
            color='project',  # Farbe nach Projekt
            hover_name='project',  # Projektname wird beim Hover angezeigt
            size_max=60,  # Maximale Größe der Blasen
            title='Bubble Chart: Project Risk vs. Priority',
            labels={
                'priority': 'Project Priority',
                'worst_case': 'Worst Case (CHF)',
                'average_cost': 'Average Cost (CHF)'
            }
        )

        # Schritt 5: Layout anpassen
        fig.update_layout(
            xaxis_title='Project Priority',
            yaxis_title='Worst Case (CHF)',
            height=600,
            width=900
        )

        # Schritt 6: Zeige den Bubble Chart in Streamlit an
        st.plotly_chart(fig)





        # Schritt 1: Definiere die Gewichtung für jedes Szenario
        weights = {
            'estimated': 0.5,
            'conservative': 0.3,
            'worst_case': 0.2
        }

        # Schritt 2: Berechne den Weighted Average Risk Index (WARI) für jedes Projekt
        df['WARI'] = (df['estimated'] * weights['estimated'] +
                    df['conservative'] * weights['conservative'] +
                    df['worst_case'] * weights['worst_case'])

        # Schritt 3: Aggregiere den WARI nach Projekt
        wari_per_project = df.groupby('project')['WARI'].sum().reset_index()

        # Schritt 4: Visualisiere den WARI pro Projekt in einem Balkendiagramm
        fig = px.bar(
            wari_per_project,
            x='project',
            y='WARI',
            title="Weighted Average Risk Index (WARI) per Project",
            labels={'WARI': 'Weighted Average Risk Index', 'project': 'Project'},
            text='WARI',
            height=500,
            template='plotly_white'
        )

        # Layout-Anpassungen
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(
            xaxis_title="Project",
            yaxis_title="Weighted Average Risk Index (WARI)",
            showlegend=False,
            margin=dict(l=50, r=50, t=80, b=40)
        )

        # Zeige das Diagramm in Streamlit an
        st.plotly_chart(fig)


        

    with tab3: 
        st.header("Edit Expenses")
        st.write("")


        # Funktion zum Ermitteln der nächsten freien ID
        def get_next_id():
            try:
                response = table.scan(ProjectionExpression="id")
                existing_ids = [int(item["id"]) for item in response.get("Items", []) if item["id"].isdigit()]
                return str(max(existing_ids) + 1) if existing_ids else "1"
            except Exception as e:
                st.error(f"Error retrieving next ID: {e}")
                return "1"
        
        # Funktion zum Einfügen eines neuen Eintrags in DynamoDB
        def insert_expense(project, title, description, date, exact_amount, estimated, conservative, worst_case, priority, status="not assigned"):
            try:
                expense_id = get_next_id()  # Neue ID berechnen
                expense_item = {
                    "id": expense_id,  # Fortlaufende ID statt UUID
                    "project": project,
                    "title": title,
                    "description": description,
                    "expense_date": str(date) if date else None,
                    "exact_amount": str(exact_amount) if exact_amount else None,
                    "estimated": str(estimated) if estimated else None,
                    "conservative": str(conservative) if conservative else None,
                    "worst_case": str(worst_case) if worst_case else None,
                    "priority": int(priority) if priority else None,
                    "status": status
                }
                table.put_item(Item=expense_item)
                st.success(f"Expense successfully saved!")
                if st.button("Refresh to view changes"):
                    st.rerun()
            except Exception as error:
                st.error(f"Error saving expense: {error}")
                


        st.subheader("Enter an expense")

        # Dropdown für die Projektauswahl
        project = st.selectbox(
            "Select a project",
            ["oikos Conference", "Sustainability Week", "Action Days", 
            "Curriculum Change", "UN-DRESS", "ChangeHub", "oikos Solar", "oikos Catalyst", 
            "Climate Neutral Events", "oikos Consulting", "Sustainable Finance", "Oismak"]
        )

        # Radiobutton für den Status (exklusiv für die Geschäftsleitung)
        status = st.radio(
            "Set the status of this expense:",
            ("not assigned", "approved", "rejected")
        )

        # Verwende einen Container für die Strukturierung
        with st.container():
            
            # Eingabe der Felder
            title = st.text_input("Title of the expense (mandatory)")
            description = st.text_input("Description (optional)")
            
            enter_date = st.radio("Is the expense associated with a specific date, and if so, is the date known?", 
                                ("Not associated with a specific date", "specific date unknown", "specific date known"))

            if enter_date == "specific date known":
                date = st.date_input("Enter the (first) date of the expense YYYY-MM-DD").strftime('%Y-%m-%d')  # Formatierung als String
            elif enter_date == "specific date unknown":
                date = "unknown"
            else:
                date = None

        # Zweiter Container für Beträge
        with st.container():
            guaranteed_amount = st.radio("Is the amount of the expense guaranteed (there is a bill or binding offer) or does it have to be estimated?", 
                                        ("Exact amount known", "Estimation"))

            if guaranteed_amount == "Exact amount known":
                exact_amount = st.number_input("Enter the exact amount of the expense in CHF")
                estimated = None
                conservative = None
                worst_case = None
            elif guaranteed_amount == "Estimation":
                exact_amount = None
                col1, col2, col3 = st.columns(3)  # Spalten für die geschätzten Beträge
                with col1:
                    estimated = st.number_input("Estimated amount in CHF")
                with col2:
                    conservative = st.number_input("Conservative estimate in CHF")
                with col3:
                    worst_case = st.number_input("Worst-case amount in CHF")

        # Eingabe für Priorität
        priority = st.number_input("Priority of the expense", min_value=1, max_value=5)

        # Submit-Button
        if st.button("Submit"):
            # Überprüfen, ob das Pflichtfeld Titel ausgefüllt ist
            if title:
                insert_expense(project, title, description, date, exact_amount, estimated, conservative, worst_case, priority, status)
            else:
                st.error("Title is a mandatory field!")





        # Funktion zum Löschen eines Eintrags
        def delete_expense_by_id(expense_id):
            try:
                expense_id_str = str(expense_id)  # Stelle sicher, dass die ID als String übergeben wird
                table.delete_item(Key={"id": expense_id_str})
                st.success(f"Expense successfully deleted!")
            except Exception as error:
                st.error(f"Error deleting expense: {error}")


        # ID-Eingabefeld zum Löschen
        st.write("")
        st.subheader("Delete an expense")
        expense_id_to_delete = st.number_input("Enter the ID of the expense you want to delete", step=1)

        # Verwende Session-State, um den Zustand des überprüften Eintrags zu speichern
        if "checked_expense" not in st.session_state:
            st.session_state["checked_expense"] = None

        # Button "Check" zur Überprüfung des Eintrags
        if st.button("Check"):
            if expense_id_to_delete:
                try:
                    expense_id_str = str(expense_id_to_delete)  # ID in String umwandeln
                    response = table.get_item(Key={"id": expense_id_str})
                    entry = response.get("Item")
        
                    if entry:
                        st.session_state["checked_expense"] = entry  # Speichere den Eintrag im Session-State
                    else:
                        st.error(f"No entry found with ID {expense_id_str}")
        
                except Exception as error:
                    st.error(f"Error fetching expense: {error}")
        
        # Zeige den überprüften Eintrag an
        if st.session_state["checked_expense"]:
            entry = st.session_state["checked_expense"]
        
            # Stelle sicher, dass der Key "project" existiert
            project_name = entry.get("project", "Unknown")
            color = get_color(project_name)
        
            container_content = f"""
                <div style='background-color: {color}; padding: 15px; border-radius: 10px; margin-bottom: 10px;'>
                    <p><strong>ID: </strong>{entry["id"]}</p>
                    <p><strong>Project: </strong>{entry["project"]}</p>
                    <h4>{entry["title"]}</h4>
                    <p>{entry["description"]}</p>
                    <p><strong>Date: </strong>{entry["expense_date"]}</p>
                    <p><strong>Amount: </strong>CHF {entry["exact_amount"] if entry["exact_amount"] is not None else f"{entry['estimated']} / {entry['conservative']} / {entry['worst_case']}"}</p>
                    <p><strong>Priority: </strong>{entry["priority"]}</p>
                </div>
            """
            st.markdown(container_content, unsafe_allow_html=True)
        
            # Button zum Löschen anzeigen
            if st.button("Delete"):
                delete_expense_by_id(expense_id_to_delete)
                st.session_state["checked_expense"] = None  # Eintrag aus Session-State löschen
        
                if st.button("Refresh to view changes"):
                    st.rerun()



# Funktion zum Überprüfen des Passworts
def check_password(username, password):
    if username in users:
        return users[username] == hashlib.sha256(password.encode()).hexdigest()
    return False

# Login-Funktion mit st.rerun()
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if check_password(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["user"] = user_names[username]
            # Seite sofort neu laden
            st.rerun()  # Verwende st.rerun() um die Seite neu zu laden
        else:
            st.error("Incorrect username or password")

# Hauptanwendung - initialisiere zuerst 'logged_in'
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Zeige entweder die App oder die Login-Seite an
if st.session_state["logged_in"]:
    app()  # Starte die Hauptanwendung, wenn der Benutzer eingeloggt ist
else:
    login()  # Zeige die Login-Seite, wenn der Benutzer nicht eingeloggt ist
