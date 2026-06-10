from flask import request, make_response
import mysql.connector
import re 
import json
from dotenv import load_dotenv
import os

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from functools import wraps

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

UPLOAD_ITEM_FOLDER = './images'

# google_spread_sheet_key = "1BqCU07MWKo01ES7ahzMWS9vA1WFNDlNrjMRTo5oUAAM"
google_spread_sheet_key = os.getenv('google_spread_sheet_key')
allowed_languages = ["english", "danish", "spanish"]
default_language = "english"
baseURL = os.environ.get("BASE_URL", "http://127.0.0.1:800")
##############################
 
def lans(key):
    try:
        # 1. Get the folder where this python file lives
        current_folder = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Build the full path to dictionary.json
        full_path = os.path.join(current_folder, "dictionary.json")
        
        # 3. Open using the full path
        with open(full_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        return data[key][default_language]
    except Exception as e:
        # Fallback if the file or key is missing (prevents crash)
        print(f"Dictionary Error: {e}")
        return key

##############################
def db():
    try:
        # Connect to the database (both pythonanywhere and local)
        db = mysql.connector.connect(
            host     = os.environ.get("DB_HOST", "mariadb"),
            user     = os.environ.get("DB_USER", "root"),
            password = os.environ.get("DB_PASS", "password"),
            database = os.environ.get("DB_NAME", "x")
        )
        cursor = db.cursor(dictionary=True)
        return db, cursor
    except Exception as ex:
        print(ex, flush=True)
        raise Exception("Twitter exception - Database under maintenance", 500)


##############################
def no_cache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache_view


##############################
REGEX_EMAIL = "^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$"
def validate_user_email(lan):
    user_email = request.form.get("user_email", "").strip()
    if not re.match(REGEX_EMAIL, user_email): raise Exception(lans("invalid_email"), 400)
    return user_email

##############################
USER_USERNAME_MIN = 2
USER_USERNAME_MAX = 20
REGEX_USER_USERNAME = f"^.{{{USER_USERNAME_MIN},{USER_USERNAME_MAX}}}$"
def validate_user_username():
    user_username = request.form.get("user_username", "").strip()
    error = f"username min {USER_USERNAME_MIN} max {USER_USERNAME_MAX} characters"
    if len(user_username) < USER_USERNAME_MIN: raise Exception(error, 400)
    if len(user_username) > USER_USERNAME_MAX: raise Exception(error, 400)
    return user_username

##############################
USER_FIRST_NAME_MIN = 2
USER_FIRST_NAME_MAX = 20
REGEX_USER_FIRST_NAME = f"^.{{{USER_FIRST_NAME_MIN},{USER_FIRST_NAME_MAX}}}$"
def validate_user_first_name():
    user_first_name = request.form.get("user_first_name", "").strip()
    error = f"first name min {USER_FIRST_NAME_MIN} max {USER_FIRST_NAME_MAX} characters"
    if not re.match(REGEX_USER_FIRST_NAME, user_first_name): raise Exception(error, 400)
    return user_first_name


##############################
USER_LAST_NAME_MIN = 2
USER_LAST_NAME_MAX = 20
REGEX_USER_LAST_NAME = f"^.{{{USER_LAST_NAME_MIN},{USER_LAST_NAME_MAX}}}$"
def validate_user_last_name():
    user_last_name = request.form.get("user_last_name", "").strip()
    error = f"last name min {USER_LAST_NAME_MIN} max {USER_LAST_NAME_MAX} characters"
    if not re.match(REGEX_USER_LAST_NAME, user_last_name): raise Exception(error, 400)
    return user_last_name


##############################
USER_PASSWORD_MIN = 6
USER_PASSWORD_MAX = 50
REGEX_USER_PASSWORD = f"^.{{{USER_PASSWORD_MIN},{USER_PASSWORD_MAX}}}$"
def validate_user_password(lan = "english"):
    user_password = request.form.get("user_password", "").strip()
    if not re.match(REGEX_USER_PASSWORD, user_password): raise Exception(lans("invalid_password"), 400)
    return user_password




##############################
def validate_user_password_confirm():
    user_password = request.form.get("user_password_confirm", "").strip()
    if not re.match(REGEX_USER_PASSWORD, user_password): raise Exception("Twitter exception - Invalid confirm password", 400)
    return user_password


##############################
REGEX_UUID4 = "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
def validate_uuid4(uuid4 = ""):
    if not uuid4:
        uuid4 = request.values.get("uuid4", "").strip()
    if not re.match(REGEX_UUID4, uuid4): raise Exception("Twitter exception - Invalid uuid4", 400)
    return uuid4


##############################
REGEX_UUID4_WITHOUT_DASHES = "^[0-9a-f]{8}[0-9a-f]{4}4[0-9a-f]{3}[89ab][0-9a-f]{3}[0-9a-f]{12}$"
def validate_uuid4_without_dashes(uuid4 = ""):
    error = "Invalid uuid4 without dashes"
    if not uuid4: raise Exception(error, 400)
    uuid4 = uuid4.strip()
    if not re.match(REGEX_UUID4_WITHOUT_DASHES, uuid4): raise Exception(error, 400)
    return uuid4


##############################
def validate_image_upload(file, allowed_extensions):
    if not file or not file.filename:
        raise Exception("missing filename", 400)

    filename_original = file.filename
    if "." not in filename_original:
        raise Exception("x-error file invalid type", 400)

    file_extension = filename_original.rsplit(".", 1)[-1].lower()
    if file_extension not in allowed_extensions:
        raise Exception("x-error file invalid type", 400)

    file.seek(0)
    header = file.read(16)
    file.seek(0)

    signatures = {
        "jpg": header.startswith(b"\xff\xd8\xff"),
        "jpeg": header.startswith(b"\xff\xd8\xff"),
        "png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "gif": header.startswith((b"GIF87a", b"GIF89a")),
        "webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
    }

    if not signatures.get(file_extension, False):
        raise Exception("x-error file invalid type", 400)

    return file_extension

##############################
POST_MIN_LEN = 2
POST_MAX_LEN = 250
REGEX_POST = f"^.{{{POST_MIN_LEN},{POST_MAX_LEN}}}$"
def validate_post(post = ""):
    post = post.strip()
    if not re.match(REGEX_POST, post): raise Exception("x-error post", 400)
    return post

##############################
COMMENT_MIN_LEN = 1
COMMENT_MAX_LEN = 280
REGEX_COMMENT = f"^.{{{COMMENT_MIN_LEN},{COMMENT_MAX_LEN}}}$"
def validate_comment(comment = ""):
    comment = comment.strip()
    if not re.match(REGEX_COMMENT, comment): raise Exception("x-error comment", 400)
    return comment


##############################
# Helper function to get tweets consistently
def get_tweets(cursor, user_pk, offset, limit, seed=None):
    # If a seed is provided, we sort by a hashed value of the ID + Seed.
    # This creates a random order that STAYS the same for that specific user session.
    if seed:
        order_clause = "ORDER BY MD5(CONCAT(p.post_pk, %s))"
        params = (user_pk, user_pk, user_pk, user_pk, seed, offset, limit)
    else:
        order_clause = "ORDER BY p.post_created_at DESC"
        params = (user_pk, user_pk, user_pk, user_pk, offset, limit)

    q = f"""
        SELECT 
            p.post_pk, p.post_user_fk, p.post_message, p.post_media_path,
            p.post_visibility, p.post_total_likes, p.post_created_at, p.post_total_comments,
            u.user_first_name, u.user_last_name, u.user_username, u.user_avatar_path,
            (SELECT COUNT(*) FROM likes WHERE like_post_fk = p.post_pk AND like_user_fk = %s) AS is_liked_by_user,
            (SELECT COUNT(*) FROM bookmarks WHERE bookmark_post_fk = p.post_pk AND bookmark_user_fk = %s) AS is_bookmarked_by_user
        FROM posts p
        JOIN users u ON u.user_pk = p.post_user_fk
        WHERE p.post_blocked_at = 0
        AND u.user_deleted_at = 0
        AND u.user_blocked_at = 0
        AND (
            p.post_visibility = 'public'
            OR p.post_user_fk = %s
            OR (SELECT user_is_admin FROM users WHERE user_pk = %s) = 1
        )
        {order_clause}
        LIMIT %s, %s
    """
    
    cursor.execute(q, params)
    tweets = cursor.fetchall()

    for tweet in tweets:
        tweet['is_liked_by_user'] = True if tweet['is_liked_by_user'] > 0 else False
        tweet['is_bookmarked_by_user'] = True if tweet['is_bookmarked_by_user'] > 0 else False
    
    return tweets

##############################
def send_email(to_email, subject, template):
    try:
        # Create a gmail fullflaskdemomail
        # Enable (turn on) 2 step verification/factor in the google account manager
        # Visit: https://myaccount.google.com/apppasswords
        # Copy the key : pdru ctfd jdhk xxci

        # Email and password of the sender's Gmail account
        sender_email = os.getenv('sender_email')
        password = os.getenv('email_password')  # If 2FA is on, use an App Password instead

        # Receiver email address
        receiver_email = to_email
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = "X clone"
        message["To"] = to_email
        message["Subject"] = subject

        # Body of the email
        message.attach(MIMEText(template, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic("Email sent successfully!")

        return "email sent"
       
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email", 500)
    finally:
        pass
