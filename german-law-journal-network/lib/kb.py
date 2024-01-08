# written by ChatGPT4
from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
import pandas as pd


def run_query(query, parameters=None):
    # Check if query is a path to a SQL file
    if os.path.isfile(query) and query.endswith('.sql'):
        with open(query, 'r') as file:
            query = file.read()

    # Retrieve database connection info from the environment variables
    host = os.environ.get('KB_HOST')
    dbname = os.environ.get('KB_DB')
    port = os.environ.get('KB_PORT')
    user = os.environ.get('KB_USER')
    password = os.environ.get('KB_PASS')

    # Connect to the database
    conn = psycopg2.connect(
        host=host,
        dbname=dbname,
        port=port,
        user=user,
        password=password
    )

    # Create a cursor object
    cursor = conn.cursor()

    # Execute the query
    cursor.execute(query, parameters)

    # If it's a SELECT query, fetch the results and display them
    if query.strip().lower().startswith('select'):
        # Fetch the results
        result = cursor.fetchall()

        # Get column names
        column_names = [desc[0] for desc in cursor.description]

        # Create a pandas DataFrame for better display in Jupyter Notebook
        df = pd.DataFrame(result, columns=column_names)
        display_result = df
    else:
        # Commit the changes if it's not a SELECT query
        conn.commit()
        display_result = None

    # Close the cursor and connection
    cursor.close()
    conn.close()

    return display_result
