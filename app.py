import os
import boto3
import pymysql
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

BUCKET_NAME = "ashly-student-photos-2026"
AWS_REGION = "ap-south-1"

DB_HOST = "ashly-student-db.cps2uksqeoln.ap-south-1.rds.amazonaws.com"
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME", "studentdb")

s3 = boto3.client("s3", region_name=AWS_REGION)


def get_db_connection():
    if not DB_PASSWORD:
        raise RuntimeError("DB_PASSWORD environment variable is not set")

    return pymysql.connect(
        host=DB_HOST,
        port=3306,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connect_timeout=10
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    course = request.form.get("course", "").strip()
    photo = request.files.get("photo")

    if not name or not email or not course or not photo or not photo.filename:
        return "Please complete all fields and choose a photo.", 400

    filename = secure_filename(photo.filename)
    if not filename:
        return "Invalid photo filename.", 400

    try:
        s3.upload_fileobj(photo, BUCKET_NAME, filename)

        photo_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": filename},
            ExpiresIn=3600
        )

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO students (name, email, course, photo_url)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (name, email, course, photo_url))
            connection.commit()
        finally:
            connection.close()

        return "Student Registered Successfully"

    except Exception:
        app.logger.exception("Registration failed")
        return "Registration failed. Check the application logs.", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
