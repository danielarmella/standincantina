import pandas as pd
import sqlite3

# File paths
excel_file = "db.xlsx"  # Change to your Excel file
sheet_name = "cantina_user"  # Change to the correct sheet name
database_file = "db.sqlite3"  # Change to your SQLite database file
table_name = "booking_user"  # Change to your table name

table_names = [
    # ('cantina_actor', 'booking_actor'),
    # ('cantina_actorstandinmatch', 'booking_actorstandinmatch'),
    # ('cantina_ad', 'booking_ad'),
    # ('cantina_availability', 'booking_availability'),
    # ('cantina_availcheck', 'booking_availcheck'),
    # ('cantina_availcheck_stand_ins', 'booking_availcheck_standins'),
    # ('cantina_booking', 'booking_booking'),
    # ('cantina_bookingrequest', 'booking_bookingrequest'),
    # ('cantina_bookingrequest_actors', 'booking_bookingrequest_actors'),
    # ('cantina_bookingrequest_images', 'booking_bookingrequest_images'),
    # ('cantina_bookingrequestimage', 'booking_bookingrequestimage'),
    # ('cantina_dnr', 'booking_dnr'),
    # ('cantina_haircolor', 'booking_haircolor'),
    # ('cantina_incident', 'booking_incident'),
    # ('cantina_mediaupload', 'booking_mediaupload'),
    # ('cantina_project', 'booking_project'),
    # ('cantina_project_ads', 'booking_project_ads'),
    # ('cantina_review', 'booking_review'),
    # ('cantina_standin', 'booking_standin'),
    # ('cantina_user', 'booking_user'),
    # ('cantina_user_groups', 'booking_user_groups'),
    ('cantina_user_user_permissions', 'booking_user_user_permissions'),
    ]

for old_table, new_table in table_names:
    # Read Excel file
    df = pd.read_excel(excel_file, sheet_name=old_table, engine="openpyxl")

    # # OPTIONAL: Rename columns if they don't match the database schema
    # df.rename(columns={"is_stand_in": "is_standin"}, inplace=True)

    # Connect to SQLite database
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    # Insert data into the database
    df.to_sql(new_table, conn, if_exists="append", index=False)

    # Commit and close
    conn.commit()
    conn.close()

    print(f"Data from {old_table} imported successfully to {new_table}!")
