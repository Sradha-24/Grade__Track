from flask import Flask,render_template,request,redirect,session,url_for
from database import create_tables
from database import create_student_data_table
from database import insert_prediction_from_csv
import sqlite3
import os, csv
import joblib
import pandas as pd

UPLOAD_FOLDER='uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")




try:
    print("Looking for model files in:", MODEL_DIR)
    print("Files found:", os.listdir(MODEL_DIR))

    ml_model = joblib.load(os.path.join(MODEL_DIR, "performance_model.pkl"))
    ml_scaler = joblib.load(os.path.join(MODEL_DIR, "model_scaler.joblib"))
    ml_features = joblib.load(os.path.join(MODEL_DIR, "model_features.joblib"))
    ml_output_cols = joblib.load(os.path.join(MODEL_DIR, "output_columns.joblib"))

    print("✅ ML model loaded successfully")

except Exception as e:
    print("❌ ML model not found or error loading:", e)
    ml_model = None
    ml_scaler = None
    ml_features = []
    ml_output_cols = []

app=Flask(__name__)
app.secret_key="mysecretkey"

create_tables()#calling create_table function in database.py
create_student_data_table()
def get_db_connection():
    conn=sqlite3.connect("users.db")
    conn.row_factory=sqlite3.Row
    return conn

@app.route("/")
def home():
    return render_template('/index.html')

@app.route("/login",methods=['GET','POST'])
def login():
    
    if request.method == "POST":
        
        email=request.form['email']
        password=request.form['password']

        
        conn=get_db_connection()
        cursor=conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND  password=?",(email, password)
        )

        user=cursor.fetchone()
        conn.close()
        print(user)
        if user:
            session['user_id']=user['id']
            session['user_role']=user['role']
            session['user_name']=user['name']
            session['register_no']=user['register_no']

            role=user['role']

            if role == "student":
                return redirect("/student")
            elif role == "teacher":
                return  redirect("/teacher")
            elif role == "admin":
                return redirect("/admin")
            else:
                return "Invalid login details"
    return render_template('/login.html')

@app.route("/register",methods=['GET','POST'])
def register():
    if request.method == "POST":
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        role=request.form['role']
        register_no=request.form.get('register_no')

        conn=get_db_connection()
        cursor=conn.cursor()

        cursor.execute(
          "INSERT INTO users (name, email, password,role,register_no) VALUES (?,?,?,?,?)",(name,email,password,role,register_no)
        )

        conn.commit()
        conn.close()

        return redirect(url_for('login'))
    return render_template("/register.html")

@app.route('/student')
def student_dashboard():

    
    if "user_id" not in session:
        return redirect("/login")
    
    user_id=session["user_id"]

    conn=get_db_connection()
    cursor=conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE id=?",(user_id,)
    )
    user=cursor.fetchone()
    conn.close()

    return render_template("student_dashboard.html",user=user)

@app.route('/admin')
def admin():
    conn=get_db_connection()
    cursor=conn.cursor()

    cursor.execute("SELECT * FROM users")
    users=cursor.fetchall()

    conn.close()
    return render_template("admin_dashboard.html",users=users)

@app.route("/teacher")
def teacher():
    if "user_id" not in session:
        return redirect("/login")
    
    user_id=session['user_id']

    conn=get_db_connection()

    cursor=conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE id=?",(user_id,)
    )
    user=cursor.fetchone()

    return render_template("teacher_dashboard.html",user=user)

@app.route('/logout')
def logout():
    return render_template('index.html')

@app.route('/teacher/upload', methods=['GET','POST'])
def teacher_upload():
    message = ""

    if request.method == "POST":
        class_id = request.form['class_id']
        semester = request.form['semester']
        model_name = request.form['model']
        file = request.files['file']

        if file.filename == "":
            message = "No file selected"
        else:
            df = pd.read_csv(file)
            #class_id, semester, model_name, df, ml_model,ml_scaler,ml_output_cols
            insert_prediction_from_csv(class_id, semester, model_name, df, ml_model, ml_features, ml_scaler, ml_output_cols)

            message = "File uploaded and predictions saved successfully." if ml_model else \
                      "File uploaded successfully (ML model not available)."

    return render_template("upload_data.html", message=message)



@app.route("/teacher/class_performance", methods=['GET','POST'])
def class_performance():
    message=" "
    performance_data=[]

    if request.method == "POST":
        class_id =request.form['class_id']
        semester = request.form['semester']
        model = request.form['model']

        conn=sqlite3.connect("users.db")
        conn.row_factory=sqlite3.Row
        cursor=conn.cursor()

        #fetch prediction for the given class
        cursor.execute("""
       SELECT register_no, student_name, sub1_level, sub2_level, sub3_level, sub4_level, overall_result
            FROM predictions
            WHERE class_id = ?
                       AND semester = ?
                       AND model = ?
""",(class_id,semester,model))
        
        performance_data=cursor.fetchall()
        conn.close()

        if not performance_data:
            message=f"No data found for class ID:{class_id}"
    return render_template("class_performance.html",performance_data=performance_data,message=message)

@app.route("/teacher/student_performance", methods=['GET','POST'])
def student_performance():
    message = ""
    student_data = []
    improvement=""

    if request.method == "POST":
        register_no = request.form.get('register_no','').strip()
        if not register_no:
            return render_template("student_performance.html",message="Please enter a Register Number",student_data=[])

        conn = sqlite3.connect("users.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT register_no, student_name, class_id, semester,
                   sub1_level, sub2_level, sub3_level, sub4_level, overall_result
            FROM predictions
            WHERE register_no = ?
            ORDER BY semester ASC
        """, (register_no,))

        student_data = cursor.fetchall()
        conn.close()

        if not student_data:
            message = "No data found for this Register Number"

       
        if len(student_data)>=2:
            first =student_data[0]['overall_result']
            last =student_data[-1]['overall_result']

            if first == "Poor" and last in ["Average","Excellent"]:
                improvement="Student has shown improvement"
            elif first == "Excellent" and last == "Poor":
                improvement = "Student performance declined"
            else:
                improvement = "Student performance is stable"
    return render_template("student_performance.html",
                           student_data=student_data,
                           message=message,improvement=improvement)
@app.route("/student/performance")
def student_performance_dashboard():

    
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id=session['user_id']
    register_no=session.get("register_no")

    conn=get_db_connection()
    cursor=conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id= ?",(user_id,))
    user=cursor.fetchone()

    cursor.execute("""
 SELECT semester,model, sub1_level, sub2_level, sub3_level, sub4_level, overall_result
        FROM predictions
        WHERE register_no = ?
        ORDER BY semester ASC
""",(register_no,))
    
    student_data = cursor.fetchall()
    conn.close()

    improvement = ""
    if len(student_data) >= 2:
        first = student_data[0]["overall_result"]
        last = student_data[-1]["overall_result"]

        score_map = {"Poor":1, "Average":2, "Excellent":3}
        if score_map[last] > score_map[first]:
            improvement = "You have improved your performance 👏"
        elif score_map[last] < score_map[first]:
            improvement = "Your performance has declined ⚠️"
        else:
            improvement = "Your performance is stable 👍"
    
    return render_template(
        "performance.html",user=user,
        student_data=student_data,
        improvement=improvement
    )

@app.route("/view_profile")
def view_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id =session['user_id']

    conn=get_db_connection()
    cursor=conn.cursor()

    cursor.execute(
        "SELECT id, name, email, role, register_no FROM users WHERE id = ?",
        (user_id,)
    )

    user=cursor.fetchone()
    conn.close()

    return render_template("student_profile.html",user=user)