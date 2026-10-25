from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import get_db_connection

app = Flask(__name__)
app.secret_key = "student_project_secret_2026"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == "admin" and password == "Admin@123":
            session["logged_in"] = True
            return redirect(url_for("dashboard"))

        flash("Username ya password galat hai.")
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Aap successfully logout ho gaye.")
    return redirect(url_for("login"))




@app.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    cursor.execute("SELECT * FROM students ORDER BY id DESC")
    students = cursor.fetchall()

    cursor.execute("""
        SELECT s.name, sub.subject_name, m.exam_name,
               m.score, m.max_score
        FROM marks m
        JOIN students s ON s.id = m.student_id
        JOIN subjects sub ON sub.id = m.subject_id
        ORDER BY m.id DESC
    """)
    marks = cursor.fetchall()
    cursor.execute("""
        SELECT s.name, s.roll_no,
               COUNT(a.id) AS total_days,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_days,
               ROUND(
                   100.0 * SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)
                   / NULLIF(COUNT(a.id), 0), 2
               ) AS attendance_percentage
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id, s.name, s.roll_no
        ORDER BY s.name
    """)
    attendance_records = cursor.fetchall()

    cursor.close()
    connection.close()

   
    return render_template(
        "dashboard.html",
        total_students=total_students,
        students=students,
        marks=marks,
        attendance_records=attendance_records,
        chart_marks=marks,
        chart_attendance=attendance_records
    )

@app.route("/add-student", methods=["POST"])
def add_student():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    roll_no = request.form.get("roll_no", "").strip()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    class_name = request.form.get("class_name", "").strip()

    if not roll_no or not name or not class_name:
        flash("Roll number, name aur class bharna zaroori hai.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO students (roll_no, name, email, class_name) "
            "VALUES (%s, %s, %s, %s)",
            (roll_no, name, email or None, class_name)
        )
        connection.commit()
        flash("Student successfully add ho gaya!")
    except Exception as error:
        connection.rollback()
        if getattr(error, "errno", None) == 1062:
            flash("Ye roll number pehle se maujood hai.")
        else:
            print("Student error:", error)
            flash("Student add nahi hua. Terminal mein error check karo.")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("dashboard"))


@app.route("/add-marks", methods=["POST"])
def add_marks():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    student_id = request.form.get("student_id", "").strip()
    subject_name = request.form.get("subject_name", "").strip()
    exam_name = request.form.get("exam_name", "").strip()
    score = request.form.get("score", "").strip()
    max_score = request.form.get("max_score", "").strip()

    connection = None
    cursor = None

    try:
        student_id = int(student_id)
        score = float(score)
        max_score = float(max_score)

        if not subject_name or not exam_name:
            flash("Subject aur exam ka naam bharo.")
            return redirect(url_for("dashboard"))

        if max_score <= 0 or score < 0 or score > max_score:
            flash("Marks sahi bharo.")
            return redirect(url_for("dashboard"))

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO subjects (subject_name) VALUES (%s) "
            "ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
            (subject_name,)
        )
        subject_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO marks "
            "(student_id, subject_id, exam_name, score, max_score) "
            "VALUES (%s, %s, %s, %s, %s)",
            (student_id, subject_id, exam_name, score, max_score)
        )

        connection.commit()
        flash("Marks successfully save ho gaye!")

    except (ValueError, TypeError):
        flash("Student select karo aur valid marks bharo.")
    except Exception as error:
        if connection is not None and connection.is_connected():
            connection.rollback()
        print("Marks error:", error)
        flash("Marks save nahi hue. Terminal mein error check karo.")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return redirect(url_for("dashboard"))

@app.route("/attendance", methods=["POST"])
def mark_attendance():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    student_id = request.form.get("student_id", "").strip()
    attendance_date = request.form.get("attendance_date", "").strip()
    status = request.form.get("status", "").strip()

    connection = None
    cursor = None

    try:
        student_id = int(student_id)

        if not attendance_date or status not in ("Present", "Absent"):
            flash("Date aur attendance status sahi bharo.")
            return redirect(url_for("dashboard"))

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO attendance (student_id, attendance_date, status)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status)
            """,
            (student_id, attendance_date, status)
        )

        connection.commit()
        flash("Attendance successfully save ho gayi!")

    except (ValueError, TypeError):
        flash("Student select karo aur valid date bharo.")
    except Exception as error:
        if connection is not None and connection.is_connected():
            connection.rollback()
        print("Attendance error:", error)
        flash("Attendance save nahi hui. Terminal mein error check karo.")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)