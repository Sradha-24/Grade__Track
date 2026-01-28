import sqlite3
import pandas as pd


def get_connection():
    conn=sqlite3.connect("users.db")
    conn.row_factory=sqlite3.Row
    return conn

def create_tables():
    conn=get_connection()
    cursor=conn.cursor()

#login table
    cursor.execute("""
     CREATE TABLE IF NOT
     EXISTS users(id INTEGER
     PRIMARY KEY AUTOINCREMENT,
     name TEXT NOT NULL, email 
    TEXT UNIQUE NOT NULL, 
    password TEXT NOT NULL, 
    role TEXT NOT NULL)
""")
    
    #prediction table
    cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   register_no TEXT,
                   student_name TEXT,
                   class_id TEXT,
                   semester TEXT,
                   model TEXT,
                   sub1_level TEXT,
                   sub2_level TEXT,
                   sub3_level TEXT,
                   sub4_level TEXT,
                   overall_result TEXT,
                   sub1_attn_level TEXT,
                   sub2_attn_level TEXT,
                   sub3_attn_level TEXT,
                   sub4_attn_level TEXT
                   )
""")
    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS subject_predictions(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   prediction_id INTEGER,
                   subject TEXT,
                   subject_mark REAL,
                   attendance INTEGER,
                   FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE);
""")
    
    conn.commit()
    conn.close()

def create_student_data_table():
    conn=get_connection()
    cursor=conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_data(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   register_no TEXT,
                   student_name TEXT,
                   sub1_series INTEGER,
                   sub2_series INTEGER,
                   sub3_series INTEGER,
                   sub4_series INTEGER,
                   sub1_attn INTEGER,
                   sub2_attn INTEGER,
                   sub3_attn INTEGER,
                   sub4_attn INTEGER,
                   class_id TEXT,
                   semester TEXT)
""")
    conn.commit()
    conn.close()


def insert_prediction_from_csv(class_id, semester, model_name, df, ml_model,ml_features,ml_scaler,ml_output_cols):
    conn=sqlite3.connect("users.db")
    cursor=conn.cursor()

    for _,row in df.iterrows():
        sub1_level = sub2_level = sub3_level = sub4_level = overall_result = ""

        if ml_model:
            # Take only features
            X = row[ml_features].to_frame().T  # single row
            X_scaled = ml_scaler.transform(X)
            

             
            preds = ml_model.predict(X_scaled)[0]  # get first row

            sub1_level = convert_to_level(preds[0])
            sub2_level = convert_to_level(preds[1])
            sub3_level = convert_to_level(preds[2])
            sub4_level = convert_to_level(preds[3])
            overall_result = convert_to_level(preds[4])



        # Insert into predictions table
        cursor.execute("""
            INSERT INTO predictions(
                register_no, student_name, class_id, semester, model,
                sub1_level, sub2_level, sub3_level, sub4_level, overall_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['Register_No'], row['Student_Name'], class_id, semester, model_name,
            sub1_level, sub2_level, sub3_level, sub4_level, overall_result
        ))
        prediction_id = cursor.lastrowid

         # Insert attendance info into subject_predictions
        subjects = ['sub1', 'sub2', 'sub3', 'sub4']
        for sub in subjects:
            mark = row.get(f"{sub}_series", None)
            attn = row.get(f"{sub}_attn", None)
            cursor.execute("""
                INSERT INTO subject_predictions(prediction_id, subject, subject_mark, attendance)
                VALUES (?, ?, ?, ?)
            """, (prediction_id, sub, mark, attn))

    conn.commit()
    conn.close()

def convert_to_level(value):

    try:
        value = int(value)   # convert string/float to int
    except:
        return "Unknown"
    
    if value == 0:
        return "Poor"
    elif value == 1:
        return "Average"
    elif value == 2:
        return "Excellent"
    else:
        return "Unknown"
