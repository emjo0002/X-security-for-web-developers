from flask import Flask, render_template, request, session, redirect, url_for, g
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import secrets
import x 
import time
import uuid
import os
import requests
import io
import csv
import json

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

app.jinja_env.globals["datetime"] = datetime

# Set the maximum file size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
 
ITEMS_TO_SHOW = 3
ITEMS_TO_FETCH = ITEMS_TO_SHOW + 1
 
##############################
@app.before_request
def load_g_user():
    g.user = session.get("user")


##############################
def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


##############################
@app.before_request
def protect_from_csrf():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    expected_token = get_csrf_token()
    submitted_token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")

    if not secrets.compare_digest(expected_token, submitted_token or ""):
        return "invalid csrf token", 400


##############################
def validate_form_uuid(name):
    return x.validate_uuid4_without_dashes(request.form.get(name, ""))


##############################
def validate_value_uuid(name):
    return x.validate_uuid4_without_dashes(request.values.get(name, ""))


##############################
def user_can_access_post(post_pk):
    try:
        db, cursor = x.db()
        q = """
            SELECT post_user_fk, post_visibility
            FROM posts
            WHERE post_pk = %s AND post_deleted_at = 0
        """
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()
        if not post:
            return False
        if g.user.get("user_is_admin"):
            return True
        if post["post_user_fk"] == g.user["user_pk"]:
            return True
        return post.get("post_visibility", "public") == "public"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
def get_post_visibility_from_form():
    post_visibility = request.form.get("post_visibility", "public")
    if post_visibility not in ("public", "private"):
        raise Exception("invalid visibility", 400)
    return post_visibility


##############################
@app.route("/forgot-password", methods=["GET", "POST"])
@app.route("/forgot-password/<lan>", methods=["GET", "POST"])
def forgot_password(lan = "english"):
    try:
        # language handling (used for flags and translations)
        if lan not in x.allowed_languages:
            lan = "english"
        x.default_language = lan
        if request.method == "GET":
            return render_template("forgot_password.html", lan=lan)

        if request.method == "POST":
            user_email = x.validate_user_email(lan)
            reset_key = uuid.uuid4().hex

            db, cursor = x.db()
            q = "UPDATE users SET user_password_reset_key = %s WHERE user_email = %s"
            cursor.execute(q, (reset_key, user_email))
            db.commit()

            # Build absolute link and inline a personalized email HTML
            reset_url = f"{x.baseURL}/create-new-password/{lan}?key={reset_key}"

            # Fetch username for greeting
            try:
                cursor.execute("SELECT user_username FROM users WHERE user_email = %s", (user_email,))
                row_user = cursor.fetchone() or {}
                user_username = row_user.get("user_username", "")
            except Exception:
                user_username = ""

            subject = "Create a new password"
            body = f"""
            <p>Hello {user_username},</p>
            <p>You requested to update your password.</p>
            <p>Click the link below to create a new password:</p>
            <p><a href=\"{reset_url}\">Create new password</a></p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            """

            try:
                x.send_email(user_email, subject, body)
            except Exception as email_ex:
                ic(f"Failed to send reset email: {email_ex}")

            toast_ok = render_template("___toast_ok.html", message=x.lans("check_your_email"))
            return f"""<browser mix-bottom=#toast>{ toast_ok }</browser>"""

    except Exception as ex:
        ic(ex)
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/create-new-password", methods=["GET", "POST"])
@app.route("/create-new-password/<lan>", methods=["GET", "POST"])
def create_new_password(lan = "english"):
    try:
        # language handling so flags/translations work
        if lan not in x.allowed_languages:
            lan = "english"
        x.default_language = lan
        key = request.args.get("key") or request.form.get("key")
        try:
            key = x.validate_uuid4_without_dashes(key)
        except Exception:
            raise Exception(x.lans("invalid_reset_key"), 400)

        db, cursor = x.db()
        q = "SELECT user_email FROM users WHERE user_password_reset_key = %s"
        cursor.execute(q, (key,))
        row = cursor.fetchone()
        if not row:
            raise Exception(x.lans("invalid_reset_link"), 400)

        if request.method == "GET":
            return render_template("create_new_password.html", key=key, lan=lan)

        if request.method == "POST":
            user_password = x.validate_user_password(lan)
            confirm_password = x.validate_user_password_confirm()
            if user_password != confirm_password:
                raise Exception(x.lans("passwords_do_not_match"), 400)
            user_hashed_password = generate_password_hash(user_password)
            q = """
            UPDATE users 
            SET user_password = %s,
                user_password_reset_key = ''
            WHERE user_email = %s
            """
            cursor.execute(q, (user_hashed_password, row["user_email"]))
            db.commit()
            return f"""
                <browser mix-redirect="/login"></browser>
            """

    except Exception as ex:
        ic(ex)
        # User errors: show toast on the page
        if ex.args and len(ex.args) > 1 and ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<browser mix-update="#toast">{ toast_error }</browser>""", 400
        return "Server error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
##############################
def _____USER_____(): pass 
##############################
##############################
##############################

@app.get("/")
def view_index():
   
    return render_template("index.html")

##############################
@app.context_processor
def global_variables():
    return dict (
        x = x,
        user = g.user,
        csrf_token = get_csrf_token
    )

##############################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lan>", methods=["GET", "POST"])
@x.no_cache
def login(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        if session.get("user", ""): return redirect(url_for("home"))
        return render_template("login.html", lan=lan)

    if request.method == "POST":
        try:
            # Validate           
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
            # Connect to the database
            q = """
                SELECT
                    user_pk, user_email, user_password, user_username,
                    user_first_name, user_last_name, user_avatar_path,
                    user_verification_key, user_deleted_at, user_is_admin,
                    user_blocked_at
                FROM users
                WHERE user_email = %s
            """
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            if not user: raise Exception(x.lans("user_not_found"), 400)

            if user["user_deleted_at"] != 0:
                 raise Exception(x.lans("user_not_found"), 400)

            if user.get("user_blocked_at") != 0:
                raise Exception(x.lans("user_is_blocked"), 400)

            if not check_password_hash(user["user_password"], user_password):
                raise Exception(x.lans("invalid_credentials"), 400)

            if user["user_verification_key"] != "":
                raise Exception(x.lans("user_not_verified"), 400)

            user.pop("user_password")
            user["user_language"] = lan

            session["user"] = user
            return f"""<browser mix-redirect="/home"></browser>"""

        except Exception as ex:
            ic(ex)

            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-update="#toast">{ toast_error }</browser>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()




##############################
@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup/<lan>", methods=["GET", "POST"])
def signup(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan


    if request.method == "GET":
        return render_template("signup.html", lan=lan)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
            user_username = x.validate_user_username()
            user_first_name = x.validate_user_first_name()

            user_pk = uuid.uuid4().hex
            user_last_name = x.validate_user_last_name()
            user_avatar_path = "static/images/avatars/unknown.jpg"
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0
            user_deleted_at = 0
            user_is_admin = 0
            user_blocked_at = 0

            user_hashed_password = generate_password_hash(user_password)
            verification_link = f"{x.baseURL}/verify-account?key={user_verification_key}"

            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, "", user_username, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at, user_deleted_at, user_is_admin, user_blocked_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", verification_link=verification_link, lans=lan)
            # ic(email_verify_account)
            x.send_email(user_email, x.lans('verify_your_account'), email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        
        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # Database errors
            if "Duplicate entry" and user_email in str(ex): 
                toast_error = render_template("___toast_error.html", message=x.lans('email_already_registered'))
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            if "Duplicate entry" and user_username in str(ex): 
                toast_error = render_template("___toast_error.html", message=x.lans('username_already_registered'))
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()



##############################
@app.get("/home")
@x.no_cache
def home():
    try:
        
        if not g.user: return redirect(url_for("login"))
        user_pk = g.user["user_pk"]
        
        db, cursor = x.db()

        # CREATE A RANDOM SEED & SAVE IT
        # This string acts as the "key" to the shuffle order
        feed_seed = uuid.uuid4().hex
        session['feed_seed'] = feed_seed

         #  Fetch tweets
        tweets = x.get_tweets(cursor, user_pk, 0, ITEMS_TO_SHOW, seed=feed_seed)
        
        # Convert the count to a boolean for template logic
        for tweet in tweets:
            tweet['is_liked_by_user'] = True if tweet['is_liked_by_user'] > 0 else False
            tweet['is_bookmarked_by_user'] = True if tweet.get('is_bookmarked_by_user', 0) > 0 else False
            
        # ic(tweets)

        q = "SELECT trend_title, trend_message FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()
        # ic(trends)

        # Suggestions query to check if already followed
        q = """
            SELECT
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
            (SELECT COUNT(*) 
            FROM follows 
            WHERE follow_follower_fk = %s 
            AND follow_followed_fk = users.user_pk) AS is_followed_by_user
            FROM users users
            WHERE users.user_pk != %s
            AND users.user_deleted_at = 0
            AND users.user_blocked_at = 0
            AND user_is_admin = 0
            AND users.user_pk NOT IN (
                    SELECT follow_followed_fk 
                    FROM follows 
                    WHERE follow_follower_fk = %s
                )
            ORDER BY RAND()
            LIMIT 5
        """
        cursor.execute(q, (user_pk, user_pk, user_pk))
        suggestions = cursor.fetchall()

        # Convert 1/0 to Boolean for Jinja
        for suggestion in suggestions:
            suggestion['is_followed_by_user'] = True if suggestion['is_followed_by_user'] > 0 else False
        
        # Following query to get users that the current user is following
        q = """
            SELECT 
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                    FROM follows 
                    WHERE follow_follower_fk = %s 
                    AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users
            JOIN follows ON users.user_pk = follows.follow_followed_fk 
            WHERE follows.follow_follower_fk = %s
            AND user_deleted_at = 0
            AND user_blocked_at = 0
            AND user_is_admin = 0
        """
        cursor.execute(q, (user_pk, user_pk))
        following = cursor.fetchall()

         # Convert 1/0 to Boolean for Jinja
        for follow in following:
            follow['is_followed_by_user'] = True if follow['is_followed_by_user'] > 0 else False

        lan = session["user"]["user_language"]

        return render_template("home.html", lan=lan, tweets=tweets, trends=trends, suggestions=suggestions, following=following, user=g.user, next_page=2)
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.route("/verify-account", methods=["GET"])
def verify_account():
    try:
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception("Invalid key", 400)
        return redirect( url_for('login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        if ex.args[1] == 400: return ex.args[0], 400    

        # System or developer error
        return "Cannot verify user"

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/logout")
def logout():
    try:
        session.clear()
        return redirect(url_for("login"))
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass



##############################
@app.get("/home-comp")
def home_comp():
    try:

        if not g.user:
            return "invalid user"
        
        # RETRIEVE THE EXISTING SEED
        feed_seed = session.get('feed_seed')

        db, cursor = x.db()
        db, cursor = x.db()
        
        #  Fetch tweets
        tweets = x.get_tweets(cursor, g.user["user_pk"], 0, ITEMS_TO_SHOW, seed=feed_seed)

        html = render_template("_home_comp.html", tweets=tweets, user=g.user, next_page=2)
        return f"""<browser mix-update="main">{ html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/api-get-posts")
def api_get_posts():
    try:
        time.sleep(1.5)  # Simulate network delay
        if not g.user: return "Access denied", 403
        
        # Calculate pagination
        next_page = int(request.args.get("page", "1"))
        offset = (next_page - 1) * ITEMS_TO_SHOW
        
        # RETRIEVE THE EXISTING SEED
        feed_seed = session.get('feed_seed')

        db, cursor = x.db()
        
        # USE THE HELPER (Fetch +1 item to see if there is a next page)
        tweets = x.get_tweets(cursor, g.user["user_pk"], offset, ITEMS_TO_FETCH, seed=feed_seed)
        
        # Check if we have more items than we need to show
        has_more_items = len(tweets) > ITEMS_TO_SHOW
        tweets_to_render = tweets[:ITEMS_TO_SHOW]
        
        container = ""
        for tweet in tweets_to_render:
            container += render_template("_tweet.html", tweet=tweet, user=g.user)

        # Logic for the "Show More" button
        if has_more_items:
            new_hyperlink = render_template("___show_more.html", next_page=next_page + 1)
        else:
            new_hyperlink = "" # No button if no more tweets

        return f"""
        <mix-html mix-bottom="#posts">
            {container}
        </mix-html>
        <mix-html mix-replace="#show_more">
            {new_hyperlink}
        </mix-html>
        """
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/bookmarks-comp")
def bookmarks_comp():
    try:
        if not g.user:
            return "invalid user"

        user_pk = g.user["user_pk"]
        db, cursor = x.db()
        if g.user.get("user_is_admin"):
            q = """
                SELECT 
                    p.post_pk, p.post_user_fk, p.post_message, p.post_media_path, p.post_visibility, p.post_total_likes, p.post_created_at, p.post_total_comments,
                    u.user_first_name, u.user_last_name, u.user_username, u.user_avatar_path,
                    (SELECT COUNT(*) FROM likes WHERE like_post_fk = p.post_pk AND like_user_fk = %s) AS is_liked_by_user,
                    1 AS is_bookmarked_by_user
                FROM bookmarks b
                JOIN posts p ON p.post_pk = b.bookmark_post_fk
                JOIN users u ON u.user_pk = p.post_user_fk
                WHERE b.bookmark_user_fk = %s AND p.post_blocked_at = 0
                ORDER BY b.bookmarked_at DESC
            """
            cursor.execute(q, (user_pk, user_pk))
        else:
            q = """
                SELECT 
                    p.post_pk, p.post_user_fk, p.post_message, p.post_media_path, p.post_visibility, p.post_total_likes, p.post_created_at, p.post_total_comments,
                    u.user_first_name, u.user_last_name, u.user_username, u.user_avatar_path,
                    (SELECT COUNT(*) FROM likes WHERE like_post_fk = p.post_pk AND like_user_fk = %s) AS is_liked_by_user,
                    1 AS is_bookmarked_by_user
                FROM bookmarks b
                JOIN posts p ON p.post_pk = b.bookmark_post_fk
                JOIN users u ON u.user_pk = p.post_user_fk
                WHERE b.bookmark_user_fk = %s
                  AND p.post_blocked_at = 0
                  AND (p.post_visibility = 'public' OR p.post_user_fk = %s)
                ORDER BY b.bookmarked_at DESC
            """
            cursor.execute(q, (user_pk, user_pk, user_pk))
        tweets = cursor.fetchall()

        for tweet in tweets:
            tweet['is_liked_by_user'] = True if tweet.get('is_liked_by_user', 0) > 0 else False
            tweet['is_bookmarked_by_user'] = True

        html = render_template("bookmarks.html", tweets=tweets, user=g.user)
        return f"""<browser mix-update="main">{ html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


 


##############################
@app.get("/profile")
def profile():
    try:
        
        if not g.user: return "invalid user"

        lan = session["user"]["user_language"]
        profile_html = render_template("_profile.html", x=x, user=g.user, lan=lan)
        return f"""<browser mix-update="main">{ profile_html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass


##############################
@app.get("/admin")
def admin():
    try:
        if not g.user: return redirect(url_for("login"))
        
        # Only allow admins; others go back to home
        if not g.user.get("user_is_admin"):
            return redirect(url_for("home"))

        lan = session["user"]["user_language"]
        
        # Get all non-admin users
        db, cursor = x.db()
        q = """
        SELECT user_pk, user_username, user_first_name, user_blocked_at
        FROM users
        WHERE user_is_admin = 0
          AND user_deleted_at = 0
        ORDER BY user_username
        """
        cursor.execute(q)
        users = cursor.fetchall()

        html = render_template("_admin.html", user=g.user, users=users, lan=lan, x=x)
        return f"""<browser mix-update="main">{ html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/admin-users-section")
def admin_users_section():
    try:
        if not g.user:
            return redirect(url_for("login"))

        if not g.user.get("user_is_admin"):
            return redirect(url_for("home"))

        db, cursor = x.db()
        q = """
        SELECT user_pk, user_username, user_first_name, user_blocked_at
        FROM users
        WHERE user_is_admin = 0
        ORDER BY user_username
        """
        cursor.execute(q)
        users = cursor.fetchall()

        nav_html = render_template("___admin_nav.html")
        content_html = render_template("_admin_users.html", users=users, user=g.user, x=x)

        return f"""
        <browser mix-update="#admin_nav">{ nav_html }</browser>
        <browser mix-update="#admin_content">{ content_html }</browser>
        """
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/admin-posts-section")
def admin_posts_section():
    try:
        if not g.user:
            return redirect(url_for("login"))

        if not g.user.get("user_is_admin"):
            return redirect(url_for("home"))
        
        lan = session["user"]["user_language"]

        db, cursor = x.db()
        
        q = """
            SELECT 
                p.post_pk,
                p.post_user_fk,
                p.post_message,
                p.post_media_path,
                p.post_visibility,
                p.post_total_likes,
                p.post_blocked_at,
                p.post_created_at,
                p.post_total_comments,
                u.user_first_name,
                u.user_last_name,
                u.user_username,
                u.user_avatar_path,
                (
                    SELECT COUNT(*) 
                    FROM likes 
                    WHERE like_post_fk = p.post_pk AND like_user_fk = %s
                ) AS is_liked_by_user
            FROM posts p
            JOIN users u ON u.user_pk = p.post_user_fk 
            WHERE p.post_blocked_at != 0
            ORDER BY p.post_blocked_at DESC
        """
        cursor.execute(q, (g.user["user_pk"],))
        blocked_posts = cursor.fetchall()

        content_html = render_template("_admin_posts.html", blocked_posts=blocked_posts, user=g.user, x=x, lan=lan)
        nav_html = render_template("___admin_nav.html")

        return f"""
        <browser mix-update="#admin_nav">{ nav_html }</browser>
        <browser mix-update="#admin_content">{ content_html }</browser>
        """
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/api-admin-block-user")
def api_admin_block_user():
    try:
        admin_user = g.user
        if not admin_user:
            return "invalid user", 401
        if not admin_user.get("user_is_admin"):
            return "forbidden", 403

        username = request.form.get("user_username", "").strip()
        blocked_user_pk = validate_form_uuid("user_pk")
        if not username:
            return "missing username", 400
        if not blocked_user_pk:
            return "missing user_pk", 400

        db, cursor = x.db()

        # Blocks the user by setting the blocked timestamp
        cursor.execute(
            "UPDATE users SET user_blocked_at = %s WHERE user_pk = %s",
            (int(time.time()), blocked_user_pk)
        )

        current_user_pk = admin_user["user_pk"]

        # Removes the blocked user from SUGGESTIONS (who to follow) for the current user
        q = """
            SELECT
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                 FROM follows 
                 WHERE follow_follower_fk = %s 
                   AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users users
            WHERE users.user_pk != %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
              AND users.user_pk NOT IN (
                    SELECT follow_followed_fk 
                    FROM follows 
                    WHERE follow_follower_fk = %s
              )
            ORDER BY RAND()
            LIMIT 5
        """
        cursor.execute(q, (current_user_pk, current_user_pk, current_user_pk))
        suggestions = cursor.fetchall()

        for suggestion in suggestions:
            suggestion["is_followed_by_user"] = suggestion["is_followed_by_user"] > 0
            suggestion.pop("user_password", None)

        # Removes the blocked user FOLLOWING for the current user
        q = """
            SELECT 
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                    FROM follows 
                    WHERE follow_follower_fk = %s 
                      AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users
            JOIN follows ON users.user_pk = follows.follow_followed_fk 
            WHERE follows.follow_follower_fk = %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
        """
        cursor.execute(q, (current_user_pk, current_user_pk))
        following = cursor.fetchall()

        for follow in following:
            follow["is_followed_by_user"] = follow["is_followed_by_user"] > 0
            follow.pop("user_password", None)

        db.commit()

        # Attempt to send a block notification email to the affected user
        try:
            cursor.execute("SELECT user_email FROM users WHERE user_pk = %s", (blocked_user_pk,))
            user_row = cursor.fetchone()
            if user_row and user_row.get("user_email"):
                blocked_email = user_row["user_email"]
                subject = "Your account has been blocked"
                body = f"""
                <p>Hello {username},</p>
                <p>Your account has been blocked by an administrator.</p>
                <p>If you believe this is a mistake, please contact support.</p>
                """
                x.send_email(blocked_email, subject, body)
        except Exception as email_ex:
            ic(f"Failed to send block email: {email_ex}")

        btn_html = render_template("___button_unblock_user.html", user_username=username, user_pk=blocked_user_pk)
        toast_ok = render_template("___toast_ok.html", message=x.lans("toast_user_blocked"))
        who_to_follow_html = render_template("_who_to_follow.html", suggestions=suggestions, following=following)
        following_html = render_template("_following.html", following=following, suggestions=suggestions)

        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <mixhtml mix-replace="#admin_btn_{blocked_user_pk}">{btn_html}</mixhtml>
            <mixhtml mix-replace="#who_to_follow">{who_to_follow_html}</mixhtml>
            <mixhtml mix-replace="#following">{following_html}</mixhtml>
        """, 200

    except Exception as ex:
        ic(ex)
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/api-admin-unblock-user")
def api_admin_unblock_user():
    try:
        admin_user = g.user
        if not admin_user: return "invalid user", 401
        if not admin_user.get("user_is_admin"): return "forbidden", 403

        username = request.form.get("user_username", "").strip()
        user_pk = validate_form_uuid("user_pk")
        if not username: return "missing username", 400
        if not user_pk: return "missing user_pk", 400

        # Persist: reset blocked timestamp
        db, cursor = x.db()
        cursor.execute("UPDATE users SET user_blocked_at = 0 WHERE user_pk = %s", (user_pk,))

        current_user_pk = admin_user["user_pk"]

        # SUGGESTIONS (who to follow) for the current user
        q = """
            SELECT
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                 FROM follows 
                 WHERE follow_follower_fk = %s 
                   AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users users
            WHERE users.user_pk != %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
              AND users.user_pk NOT IN (
                    SELECT follow_followed_fk 
                    FROM follows 
                    WHERE follow_follower_fk = %s
              )
            ORDER BY RAND()
            LIMIT 5
        """
        cursor.execute(q, (current_user_pk, current_user_pk, current_user_pk))
        suggestions = cursor.fetchall()

        for suggestion in suggestions:
            suggestion["is_followed_by_user"] = suggestion["is_followed_by_user"] > 0
            suggestion.pop("user_password", None)

        # FOLLOWING for the current user
        q = """
            SELECT 
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                    FROM follows 
                    WHERE follow_follower_fk = %s 
                      AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users
            JOIN follows ON users.user_pk = follows.follow_followed_fk 
            WHERE follows.follow_follower_fk = %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
        """
        cursor.execute(q, (current_user_pk, current_user_pk))
        following = cursor.fetchall()

        for follow in following:
            follow["is_followed_by_user"] = follow["is_followed_by_user"] > 0
            follow.pop("user_password", None)

        db.commit()

        try:
            cursor.execute("SELECT user_email FROM users WHERE user_pk = %s", (user_pk,))
            user_row = cursor.fetchone()
            if user_row and user_row.get("user_email"):
                unblocked_email = user_row["user_email"]
                subject = "Your account has been unblocked"
                body = f"""
                <p>Hello {username},</p>
                <p>Your account has been unblocked by an administrator.</p>
                <p>You can now login to the account again</p>
                """
                x.send_email(unblocked_email, subject, body)
        except Exception as email_ex:
            ic(f"Failed to send unblock email: {email_ex}")

        btn_html = render_template("___button_block_user.html", user_username=username, user_pk=user_pk)
        toast_ok = render_template("___toast_ok.html", message=x.lans('toast_user_unblocked'))
        who_to_follow_html = render_template("_who_to_follow.html", suggestions=suggestions, following=following)
        following_html = render_template("_following.html", following=following, suggestions=suggestions)


        return f"""
            <browser mix-bottom=\"#toast\">{toast_ok}</browser>
            <mixhtml mix-replace=\"#admin_btn_{user_pk}\">{btn_html}</mixhtml>
            <mixhtml mix-replace="#who_to_follow">{who_to_follow_html}</mixhtml>
            <mixhtml mix-replace="#following">{following_html}</mixhtml>
        """, 200
    except Exception as ex:
        ic(ex)
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/api-admin-block-post")
def api_admin_block_post():
    try:
        admin_user = g.user
        if not admin_user or not admin_user.get("user_is_admin"):
            return "forbidden", 403

        post_pk = validate_form_uuid("post_pk")
        if not post_pk:
            return "missing post_pk", 400

        db, cursor = x.db()
        cursor.execute("UPDATE posts SET post_blocked_at = %s WHERE post_pk = %s", (int(time.time()), post_pk))
        db.commit()

        try:
            cursor.execute(
                """
                SELECT u.user_email, u.user_username, p.post_message, p.post_created_at
                FROM posts p
                JOIN users u ON u.user_pk = p.post_user_fk
                WHERE p.post_pk = %s
                """,
                (post_pk,)
            )
            post_row = cursor.fetchone()
            if post_row and post_row.get("user_email"):
                blocked_email = post_row["user_email"]
                subject = "Your post has been blocked"
                body = f"""
                <p>Hello @{post_row.get('user_username', '')},</p>
                <p>Your post has been blocked by an administrator.</p>
                <p><strong>Message:</strong><br>{post_row.get('post_message', '')}</p>
                <p><strong>Posted at:</strong> {post_row.get('post_created_at', '')}</p>
                <p>If you believe this is a mistake, please contact support.</p>
                """
                x.send_email(blocked_email, subject, body)
        except Exception as email_ex:
            ic(f"Failed to send post blocked email: {email_ex}")
        
        btn_html = render_template("___button_unblock_post.html", post_pk=post_pk)
        toast_ok = render_template("___toast_ok.html", message=x.lans('toast_post_blocked'))
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <mixhtml mix-replace="#block-btn-{post_pk}">{btn_html}</mixhtml>
        """, 200
    except Exception as ex:
        ic(ex)
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/api-admin-unblock-post")
def api_admin_unblock_post():
    try:
        admin_user = g.user
        if not admin_user or not admin_user.get("user_is_admin"):
            return "forbidden", 403

        post_pk = validate_form_uuid("post_pk")
        if not post_pk:
            return "missing post_pk", 400

        source = request.form.get("source", "")

        db, cursor = x.db()
        cursor.execute("UPDATE posts SET post_blocked_at = 0 WHERE post_pk = %s", (post_pk,))
        db.commit()

        try:
            cursor.execute(
                """
                SELECT u.user_email, u.user_username, p.post_message, p.post_created_at
                FROM posts p
                JOIN users u ON u.user_pk = p.post_user_fk
                WHERE p.post_pk = %s
                """,
                (post_pk,)
            )
            post_row = cursor.fetchone()
            if post_row and post_row.get("user_email"):
                unblocked_email = post_row["user_email"]
                subject = "Your post has been unblocked"
                body = f"""
                <p>Hello @{post_row.get('user_username', '')},</p>
                <p>Your post has been unblocked by an administrator.</p>
                <p><strong>Message:</strong><br>{post_row.get('post_message', '')}</p>
                <p><strong>Posted at:</strong> {post_row.get('post_created_at', '')}</p>
                <p>You can now view it again.</p>
                """
                x.send_email(unblocked_email, subject, body)
        except Exception as email_ex:
            ic(f"Failed to send post unblocked email: {email_ex}")

        toast_ok = render_template("___toast_ok.html", message=x.lans('toast_post_unblocked'))
        btn_html = render_template("___button_block_post.html", post_pk=post_pk)
        return f"""
            <browser mix-bottom=\"#toast\">{toast_ok}</browser>
            <mixhtml mix-replace=\"#block-btn-{post_pk}\">{btn_html}</mixhtml>
        """, 200
    except Exception as ex:
        ic(ex)
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
        

##############################
@app.patch("/like-tweet")
@x.no_cache
def api_like_tweet():
    try:
        if not g.user: return "invalid user", 401
        
        post_pk = validate_form_uuid("post_pk")
        if not post_pk: raise Exception("Missing post ID", 400)
        
        # Get the current Unix epoch timestamp in seconds
        current_epoch = int(time.time()) 

        db, cursor = x.db()
        if not user_can_access_post(post_pk):
            return "not allowed", 403

        # Insert a new like record with the composite key and timestamp
        q_insert_like = "INSERT INTO likes (like_user_fk, like_post_fk, like_timestamp) VALUES(%s, %s, %s)"
        cursor.execute(q_insert_like, (g.user["user_pk"], post_pk, current_epoch))
        
        db.commit()
        
        # Get the new total like count to display
        q_get_count = "SELECT post_total_likes FROM posts WHERE post_pk = %s"
        cursor.execute(q_get_count, (post_pk,))
        new_count = cursor.fetchone()["post_total_likes"]

        # Response to the browser: replace button and update count
        button_unlike_tweet = render_template("___button_unlike_tweet.html", post_pk=post_pk, like_count=new_count)
        
        
        return f"""
            <mixhtml mix-replace="#button_container_{post_pk}">
                {button_unlike_tweet}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # If already liked (Duplicate entry), just return OK with the unlike button
        if "Duplicate entry" in str(ex):
            # This is a fallback in case the frontend logic fails to use the correct button
            # We must fetch the current count to return the correct unlike button
            try:
                db, cursor = x.db()
                q_get_count = "SELECT post_total_likes FROM posts WHERE post_pk = %s"
                cursor.execute(q_get_count, (post_pk,))
                current_count = cursor.fetchone()["post_total_likes"]
                button_unlike_tweet = render_template("___button_unlike_tweet.html", post_pk=post_pk, like_count=current_count)
                return f"""<mixhtml mix-replace="#button_container_{post_pk}">{button_unlike_tweet}</mixhtml>"""
            except:
                return "Already liked, failed to get count", 400
        
        # Other errors
        if ex.args and len(ex.args) > 1 and ex.args[1] == 400:
            return ex.args[0], 400

        return "System error during like", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.patch("/unlike-tweet")
@x.no_cache
def api_unlike_tweet():
    try:
        if not g.user: return "invalid user", 401
        
        # Get post_pk from mix-data form
        post_pk = validate_form_uuid("post_pk")
        if not post_pk: raise Exception("Missing post ID", 400)

        db, cursor = x.db()

        # Delete the like record
        q_delete_like = "DELETE FROM likes WHERE like_user_fk = %s AND like_post_fk = %s"
        cursor.execute(q_delete_like, (g.user["user_pk"], post_pk))
        db.commit()

       # Get the new total like count to display
        q_get_count = "SELECT post_total_likes FROM posts WHERE post_pk = %s"
        cursor.execute(q_get_count, (post_pk,))
        new_count = cursor.fetchone()["post_total_likes"]

        # Response to the browser: replace button and update count
        button_like_tweet = render_template("___button_like_tweet.html", post_pk=post_pk, like_count=new_count)
        
        return f"""
            <mixhtml mix-replace="#button_container_{post_pk}">
                {button_like_tweet}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        # User errors
        if ex.args and len(ex.args) > 1 and ex.args[1] == 400:
            return ex.args[0], 400

        return "System error during unlike", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.patch("/bookmark-tweet")
@x.no_cache
def api_bookmark_tweet():
    try:
        if not g.user: return "invalid user", 401

        post_pk = validate_form_uuid("post_pk")
        if not post_pk: raise Exception("Missing post ID", 400)

        current_epoch = int(time.time())
        db, cursor = x.db()
        if not user_can_access_post(post_pk):
            return "not allowed", 403

        # Prevent crash on duplicates
        q = "INSERT IGNORE INTO bookmarks (bookmark_user_fk, bookmark_post_fk, bookmarked_at) VALUES (%s, %s, %s)"
        cursor.execute(q, (g.user["user_pk"], post_pk, current_epoch))
        db.commit()

        btn_html = render_template("___button_unbookmark_tweet.html", post_pk=post_pk)
        return f"""
            <mixhtml mix-replace="#bookmark_button_{post_pk}">{btn_html}</mixhtml>
        """, 200
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # Silently succeed if already bookmarked
        if "Duplicate entry" in str(ex):
            return "", 200
        if ex.args and len(ex.args) > 1 and ex.args[1] == 400:
            return ex.args[0], 400
        return "System error during bookmark", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.patch("/unbookmark-tweet")
@x.no_cache
def api_unbookmark_tweet():
    try:
        if not g.user: return "invalid user", 401

        post_pk = validate_form_uuid("post_pk")
        if not post_pk: raise Exception("Missing post ID", 400)

        db, cursor = x.db()

        q = "DELETE FROM bookmarks WHERE bookmark_user_fk = %s AND bookmark_post_fk = %s"
        cursor.execute(q, (g.user["user_pk"], post_pk))
        db.commit()

        btn_html = render_template("___button_bookmark_tweet.html", post_pk=post_pk)
        return f"""
            <mixhtml mix-replace="#bookmark_button_{post_pk}">{btn_html}</mixhtml>
        """, 200
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if ex.args and len(ex.args) > 1 and ex.args[1] == 400:
            return ex.args[0], 400
        return "System error during unbookmark", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/follow-user")
@x.no_cache
def follow_user():
    try:
        if not g.user:
            return "unauthorized", 401
        
        follower_fk = g.user["user_pk"]          # den nuværende bruger
        followed_fk = validate_form_uuid("user_pk")

        if not followed_fk:
            raise Exception("User ID missing", 400)
        
        db, cursor = x.db()

        # 1) Insert follow
        q = """
            INSERT INTO follows (follow_follower_fk, follow_followed_fk, follow_timestamp)
            VALUES (%s, %s, %s)
        """
        cursor.execute(q, (follower_fk, followed_fk, int(time.time())))
        db.commit()

        # 2) Hent opdaterede suggestions (who to follow) til den NUVÆRENDE bruger
        q_suggestions = """
            SELECT
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                 FROM follows 
                 WHERE follow_follower_fk = %s 
                   AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users users
            WHERE users.user_pk != %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
              AND users.user_is_admin = 0
              AND users.user_pk NOT IN (
                    SELECT follow_followed_fk 
                    FROM follows 
                    WHERE follow_follower_fk = %s
              )
            ORDER BY RAND()
            LIMIT 5
        """
        cursor.execute(q_suggestions, (follower_fk, follower_fk, follower_fk))
        suggestions = cursor.fetchall()

        for suggestion in suggestions:
            suggestion["is_followed_by_user"] = suggestion["is_followed_by_user"] > 0
            suggestion.pop("user_password", None)

        # 3) Hent opdateret following-list til den NUVÆRENDE bruger
        q_following = """
            SELECT 
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                 FROM follows 
                 WHERE follow_follower_fk = %s 
                   AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users
            JOIN follows ON users.user_pk = follows.follow_followed_fk 
            WHERE follows.follow_follower_fk = %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
              AND users.user_is_admin = 0
        """
        cursor.execute(q_following, (follower_fk, follower_fk))
        following = cursor.fetchall()

        for follow in following:
            follow["is_followed_by_user"] = follow["is_followed_by_user"] > 0
            follow.pop("user_password", None)

        # 4) Render HTML-fragmenter
        btn = render_template("___button_unfollow.html", user_pk=followed_fk)
        who_to_follow_html = render_template("_who_to_follow.html", suggestions=suggestions, following=following)
        following_html = render_template("_following.html", following=following, suggestions=suggestions)

        return f"""
            <mixhtml mix-replace="#follow_btn_{followed_fk}">{btn}</mixhtml>
            <mixhtml mix-replace="#who_to_follow">{who_to_follow_html}</mixhtml>
            <mixhtml mix-replace="#following">{following_html}</mixhtml>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # If already following, return success with Unfollow button to fix UI
        if "Duplicate entry" in str(ex):
            btn = render_template("___button_unfollow.html", user_pk=followed_fk)
            return f"""<mixhtml mix-replace="#follow_btn_{followed_fk}">{btn}</mixhtml>"""
        return "System Error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.patch("/unfollow-user")
@x.no_cache
def unfollow_user():
    try:
        if not g.user:
            return "unauthorized", 401

        follower_fk = g.user["user_pk"]
        followed_fk = validate_form_uuid("user_pk")

        if not followed_fk:
            raise Exception("User ID missing", 400)

        db, cursor = x.db()

        # 1) Delete from follows table
        q = """
            DELETE FROM follows 
            WHERE follow_follower_fk = %s 
              AND follow_followed_fk = %s
        """
        cursor.execute(q, (follower_fk, followed_fk))
        db.commit()

        # 2) Hent opdaterede suggestions (who to follow)
        q_suggestions = """
            SELECT
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                 FROM follows 
                 WHERE follow_follower_fk = %s 
                   AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users users
            WHERE users.user_pk != %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
              AND users.user_is_admin = 0
              AND users.user_pk NOT IN (
                    SELECT follow_followed_fk 
                    FROM follows 
                    WHERE follow_follower_fk = %s
              )
            ORDER BY RAND()
            LIMIT 5
        """
        cursor.execute(q_suggestions, (follower_fk, follower_fk, follower_fk))
        suggestions = cursor.fetchall()

        for suggestion in suggestions:
            suggestion["is_followed_by_user"] = suggestion["is_followed_by_user"] > 0
            suggestion.pop("user_password", None)

        # 3) Hent opdateret following-list for den nuværende bruger
        q_following = """
            SELECT 
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                 FROM follows 
                 WHERE follow_follower_fk = %s 
                   AND follow_followed_fk = users.user_pk
                ) AS is_followed_by_user
            FROM users
            JOIN follows ON users.user_pk = follows.follow_followed_fk
            WHERE follows.follow_follower_fk = %s
              AND users.user_deleted_at = 0
              AND users.user_blocked_at = 0
              AND users.user_is_admin = 0
        """
        cursor.execute(q_following, (follower_fk, follower_fk))
        following = cursor.fetchall()

        for follow in following:
            follow["is_followed_by_user"] = follow["is_followed_by_user"] > 0
            follow.pop("user_password", None)

        # 4) Render new fragments
        btn = render_template("___button_follow.html", user_pk=followed_fk)
        who_to_follow_html = render_template("_who_to_follow.html", suggestions=suggestions, following=following)
        following_html = render_template("_following.html", following=following, suggestions=suggestions)

        # 5) Return MixHTML updates
        return f"""
            <mixhtml mix-replace="#follow_btn_{followed_fk}">{btn}</mixhtml>
            <mixhtml mix-replace="#who_to_follow">{who_to_follow_html}</mixhtml>
            <mixhtml mix-replace="#following">{following_html}</mixhtml>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return "System Error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################

@app.route("/comments", methods=["GET", "POST"])
def comments():
    try:
        if not g.user:
            return "invalid user", 401

        # Opens the comments
        if request.method == "POST":
            post_pk = validate_form_uuid("post_pk")
            if not post_pk:
                raise Exception("Missing post ID", 400)
            
            lan = session["user"]["user_language"]

            ic(lan)

            db, cursor = x.db()
            if not user_can_access_post(post_pk):
                return "not allowed", 403

            # 1. GET the comments +  the users that belong to the comments
            q_get_all_comments = """
                SELECT
                    comments.comment_pk,
                    comments.comment_post_fk,
                    comments.comment_user_fk,
                    comments.comment_text,
                    comments.comment_updated_at,
                    comments.comment_created_at,
                    users.user_pk,
                    users.user_first_name,
                    users.user_last_name,
                    users.user_username,
                    users.user_avatar_path
                FROM comments
                JOIN users ON comments.comment_user_fk = users.user_pk
                WHERE comments.comment_post_fk = %s
                ORDER BY comments.comment_created_at ASC
            """
            cursor.execute(q_get_all_comments, (post_pk,))
            comments = cursor.fetchall()
            
            # 2. Get current comments count
            q_get_count = "SELECT post_total_comments FROM posts WHERE post_pk = %s"
            cursor.execute(q_get_count, (post_pk,))
            comments_count = cursor.fetchone()["post_total_comments"]
            
            close_comments_button = render_template("___button_close_comments.html", post_pk=post_pk, comments_count=comments_count)

            comments_template = render_template("_comments_section.html", comments=comments, post_pk=post_pk, user=g.user, lan=lan)

            return f"""
                <mixhtml mix-replace="#open_comments_button_container_{post_pk}">
                    {close_comments_button}
                </mixhtml>

                <browser mix-after="#post_actions_{post_pk}">
                    {comments_template}
                </browser>
            """
        
        # Closes the comments
        if request.method == "GET":
            post_pk = x.validate_uuid4_without_dashes(request.args.get("post_pk", ""))
            if not post_pk:
                raise Exception("Missing post ID", 400)
            
            db, cursor = x.db()
            if not user_can_access_post(post_pk):
                return "not allowed", 403

            q_get_count = "SELECT post_total_comments FROM posts WHERE post_pk = %s"
            cursor.execute(q_get_count, (post_pk,))
            comments_count = cursor.fetchone()["post_total_comments"]

            open_comments_button = render_template("___button_open_comments.html", post_pk=post_pk, comments_count=comments_count)

            return f"""
                <mixhtml mix-replace="#close_comments_button_container_{post_pk}">
                    {open_comments_button}
                </mixhtml>

                <mixhtml mix-remove="#comments_section_{post_pk}">
                </mixhtml>
            """

    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
        

#############################

@app.route("/api-create-comment", methods=["POST"])
def api_create_comment():
    try:
        if not g.user:
            return "invalid user", 401

        post_pk = validate_form_uuid("post_pk")
        if not post_pk:
            return "missing post_pk"
        
        comment_text = x.validate_comment(request.form.get("comment", ""))
        comment_pk = uuid.uuid4().hex
        current_epoch = int(time.time()) 

        lan = session["user"]["user_language"]

        db, cursor = x.db()
        if not user_can_access_post(post_pk):
            return "not allowed", 403

        # 1. Insert new comment
        q = "INSERT INTO comments VALUES(%s, %s, %s, %s, %s, %s)"
        cursor.execute(q, (comment_pk, post_pk, g.user["user_pk"], comment_text, 0, current_epoch))

        # 2. Get the new total comments count
        q_get_count = "SELECT post_total_comments FROM posts WHERE post_pk = %s"
        cursor.execute(q_get_count, (post_pk,))
        new_count = cursor.fetchone()["post_total_comments"]

        db.commit()

        # Build comment object for rendering
        comment = {
            "comment_pk": comment_pk,
            "comment_post_fk": post_pk,
            "comment_user_fk": g.user["user_pk"],
            "comment_text": comment_text,
            "comment_updated_at": 0,
            "comment_created_at": 0, 
            "user_pk": g.user["user_pk"],
            "user_first_name": g.user["user_first_name"],
            "user_last_name": g.user["user_last_name"],
            "user_username": g.user["user_username"],
            "user_avatar_path": g.user["user_avatar_path"],
        }

        html_comment_container = render_template(
            "___comment_container.html",
            post_pk=post_pk,
            lan=lan
        )

        html_comment = render_template(
            "___comment.html",
            comment=comment,
            post_pk=post_pk,
            user=g.user,
            lan=lan
        )

        html_close_comment = render_template(
            "___button_close_comments.html",
            comments_count=new_count,
            post_pk=post_pk,
        )

        return f"""
            <browser mix-remove="#no_comment_{post_pk}"></browser>

            <browser mix-top="#comments_section_{post_pk}">
                {html_comment}
            </browser>

            <browser mix-replace="#comment_container_{post_pk}">
                {html_comment_container}
            </browser>

            <browser mix-replace="#close_comments_button_container_{post_pk}">
                {html_close_comment}
            </browser>
        """
        
    except Exception as ex:
        ic(ex)
        
        if "x-error comment" in str(ex):
            toast_error = render_template(
                "___toast_error.html",
                message=f"{x.lans('comment')} - {x.COMMENT_MIN_LEN} {x.lans('to')} {x.COMMENT_MAX_LEN} {x.lans('characters')}"
            )
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################

@app.route("/api-create-post", methods=["POST"])
def api_create_post():
    db = None
    cursor = None
    
    try:

        if not g.user: return "invalid user"       

        post = x.validate_post(request.form.get("post", ""))
        post_visibility = get_post_visibility_from_form()
        post_pk = uuid.uuid4().hex
        current_epoch = int(time.time())
        post_media_path = ""
        
        # Handle file upload
        if 'post_media' in request.files:
            file = request.files['post_media']
            if file and file.filename:
                # CHECK FILE SIZE FIRST (5MB limit)
                file.seek(0, 2)
                size = file.tell()
                file.seek(0)
                
                if size > 5 * 1024 * 1024:
                    raise Exception("x-error file size too large")
                
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                x.validate_image_upload(file, allowed_extensions)
                
                # Generate unique filename
                original_filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_filename}"

                upload_dir = 'static/images'
                if not os.path.exists(upload_dir):
                    # NOTE: os.makedirs is commented out as it requires a local file system which is not available here.
                    os.makedirs(upload_dir) 
                
                # Save file (Mocking file save)
                file_path = os.path.join('static/images', unique_filename)
                file.save(file_path)
                
                # Store just the filename for database
                post_media_path = f"images/{unique_filename}"
        
        db, cursor = x.db()
        
        q = """INSERT INTO posts 
            (post_pk, post_user_fk, post_message, post_visibility, post_total_likes, post_media_path, post_blocked_at, post_created_at, post_deleted_at, post_updated_at) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, 0)"""

        cursor.execute(q, (
        post_pk,
        g.user["user_pk"],
        post,
        post_visibility,
        0,
        post_media_path,
        0,
        current_epoch, 
        0
        ))

        db.commit()
        
        toast_ok = render_template("___toast_ok.html", message=x.lans('post_live'))
        tweet = {
            "post_pk": post_pk,
            "post_user_fk": g.user["user_pk"] ,
            "user_first_name": g.user["user_first_name"],
            "user_last_name": g.user["user_last_name"],
            "user_username": g.user["user_username"],
            "user_avatar_path": g.user["user_avatar_path"],
            "post_message": post,
            "post_pk": post_pk,
            "post_media_path": post_media_path,
            "post_visibility": post_visibility,
            "post_total_likes": 0,
            "post_total_comments": 0,
            "post_blocked_at": 0,
            "is_liked_by_user": False,
            "is_bookmarked_by_user": False,
            "post_created_at": None
        }
        html_post_container = render_template("___post_container.html")
        html_post = render_template("_tweet.html", tweet=tweet, user=g.user)
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-top="#posts">{html_post}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """
    except Exception as ex:
        ic(ex)
        
        if db:
            try:
                db.rollback()
            except Exception:
                pass

        # Post validation error
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"{x.lans('post')} - {x.POST_MIN_LEN} {x.lans('to')} {x.POST_MAX_LEN} {x.lans('characters')}")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        
        # File upload errors
        if "x-error file" in str(ex):
            if "size too large" in str(ex):
                toast_error = render_template("___toast_error.html", message=x.lans('image_too_large'))
            else:
                toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

    finally:
        if cursor is not None: cursor.close()
        if db is not None: db.close()

###################################
@app.route("/api-delete-post/<post_pk>", methods=["DELETE"])
def api_delete_post(post_pk):
    
    try:
    
        # Check if user is logged in
        if not g.user:
            return "invalid user", 400

        post_pk = x.validate_uuid4_without_dashes(post_pk)

        db, cursor = x.db()

        # Delete post from database IF its the users post
        q = "DELETE FROM posts WHERE post_pk = %s and post_user_fk = %s"
        cursor.execute(q, (post_pk, g.user["user_pk"],))

        db.commit()

        toast_ok = render_template("___toast_ok.html", message=x.lans('post_deleted'))
        
        # Remove the post from the DOM + show toast
        # return "ok"
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-remove="#post_container_{post_pk}"></browser>
        """, 200

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500

    finally: 
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.route("/api-delete-comment", methods=["DELETE"])
def api_delete_comment():
    try:
        if not g.user:
            return "invalid user", 401
        
        comment_pk = x.validate_uuid4_without_dashes(request.args.get("comment_pk", ""))
        if not comment_pk:
                    return "missing comment_pk", 400
        
        post_pk = x.validate_uuid4_without_dashes(request.args.get("post_pk", ""))
        if not post_pk:
                return "missing post_pk", 400

        db, cursor = x.db()

        # 1. Delete comment but only if it belongs to the user
        q = """
        DELETE FROM comments 
        WHERE comment_pk = %s 
          AND comment_post_fk = %s 
          AND comment_user_fk = %s
        """
        cursor.execute(q, (comment_pk, post_pk, g.user["user_pk"]))
        ic("deleted rows:", cursor.rowcount)

        if cursor.rowcount == 0:
            db.rollback()
            return "not allowed", 403

        # 2. Get the new total comments count
        q_get_count = "SELECT post_total_comments FROM posts WHERE post_pk = %s"
        cursor.execute(q_get_count, (post_pk,))
        new_count = cursor.fetchone()["post_total_comments"]
        
        db.commit()

        html_close_comment = render_template(
            "___button_close_comments.html",
            comments_count=new_count,
            post_pk=post_pk
        )

        # if there are STILL comments (new_count > 0)
        if new_count > 0:
            return f"""
                <browser mix-remove="#comment_{comment_pk}"></browser>
                <browser mix-replace="#close_comments_button_container_{post_pk}">
                    {html_close_comment}
                </browser>  
            """

        # if there are NO comments left (new_count == 0)
        no_comment_html = f"""
            <p id="no_comment_{post_pk}" class="text-a-center">
                There is no comment on this post yet.
            </p>
        """

        return f"""
            <browser mix-remove="#comment_{comment_pk}"></browser>

            <browser mix-top="#comments_section_{post_pk}">
                {no_comment_html}
            </browser>

            <browser mix-replace="#close_comments_button_container_{post_pk}">
                {html_close_comment}
            </browser>  
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/api-edit-comment", methods=["GET"])
def api_edit_comment():
    try:
        if not g.user:
            return "invalid user", 401

        comment_pk = x.validate_uuid4_without_dashes(request.args.get("comment_pk", ""))
        if not comment_pk:
            return "missing comment_pk", 400
    
        post_pk = x.validate_uuid4_without_dashes(request.args.get("post_pk", ""))
        if not post_pk:
            return "missing post_pk", 400

        db, cursor = x.db()

        # Get the comment text
        q = """
        SELECT comment_text, comment_user_fk 
        FROM comments 
        WHERE comment_pk = %s
        """
        cursor.execute(q, (comment_pk,))
        row = cursor.fetchone()
        if not row or row["comment_user_fk"] != g.user["user_pk"]:
            return "not allowed", 403

        comment_text = row["comment_text"]

        html_comment_edit_form = render_template("___comment_edit_form.html", comment_pk=comment_pk, post_pk=post_pk, comment_text=comment_text)

        return f"""

        <browser mix-replace="#comment_text{ comment_pk }">{html_comment_edit_form}</browser>

        """

    except Exception as ex:
        ic(ex)

        return "error", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/api-update-comment", methods=["POST"])
def api_update_comment():
    try:
        if not g.user:
            return "invalid user", 401

        comment_pk = validate_form_uuid("comment_pk")
        if not comment_pk:
            return "missing comment_pk", 400

        post_pk = validate_form_uuid("post_pk")
        if not post_pk:
            return "missing post_pk", 400

        new_text = x.validate_comment(request.form.get("comment_text", ""))
        if not new_text:
            return "missing comment_text", 400
        
        current_epoch = int(time.time()) 

        db, cursor = x.db()

        # Update comment only if it belongs to the user
        q_update = """
        UPDATE comments 
        SET comment_text = %s,
        comment_updated_at = %s 
        WHERE comment_pk = %s AND comment_user_fk = %s
        """
        cursor.execute(q_update, (new_text,current_epoch, comment_pk, g.user["user_pk"]))
        db.commit()

        # Get the updated comment created_at
        q_get = """
        SELECT comment_created_at, comment_post_fk
        FROM comments
        WHERE comment_pk = %s AND comment_user_fk = %s
        """
        cursor.execute(q_get, (comment_pk, g.user["user_pk"]))
        the_updated_comment = cursor.fetchone()
        
        if not the_updated_comment:
            return "comment_not_found", 404

        lan = session["user"]["user_language"]

        # Build updated comment object for rendering
        comment = {
            "comment_pk": comment_pk,
            "comment_post_fk": post_pk,
            "comment_user_fk": g.user["user_pk"],
            "comment_text": new_text,
            "comment_updated_at": current_epoch,
            "comment_created_at": the_updated_comment["comment_created_at"],
            "user_pk": g.user["user_pk"],
            "user_first_name": g.user["user_first_name"],
            "user_last_name": g.user["user_last_name"],
            "user_username": g.user["user_username"],
            "user_avatar_path": g.user["user_avatar_path"]
        }

        html_comment = render_template(
            "___comment.html",
            comment=comment,
            post_pk=post_pk,
            user=g.user,
            lan=lan
        )

        toast_ok = render_template("___toast_ok.html", message=x.lans('comment_updated'))

        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#comment_{comment_pk}">
                {html_comment}
            </browser>
        """

    except Exception as ex:
        ic(ex)
        
        if "x-error comment" in str(ex):
            toast_error = render_template(
                "___toast_error.html",
                message=f"{x.lans('comment')} - {x.COMMENT_MIN_LEN} {x.lans('to')} {x.COMMENT_MAX_LEN} {x.lans('characters')}"
            )
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        return "error", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.route("/api-cancel-edit-comment", methods=["GET"])
def api_cancel_edit_comment():

    if not g.user:
        return "invalid user", 401

    comment_pk = x.validate_uuid4_without_dashes(request.args.get("comment_pk", ""))
    if not comment_pk:
            return "missing comment_pk", 400
    
    post_pk = x.validate_uuid4_without_dashes(request.args.get("post_pk", ""))
    if not post_pk:
            return "missing post_pk", 400

    db, cursor = x.db()
    q = """
    SELECT
        comments.comment_pk,
        comments.comment_text,
        comments.comment_created_at,
        comments.comment_updated_at,
        users.user_pk,
        users.user_username,
        users.user_first_name,
        users.user_last_name,
        users.user_avatar_path
    FROM comments
    JOIN users ON comments.comment_user_fk = users.user_pk
    WHERE comment_pk = %s AND comment_user_fk = %s
    """
    cursor.execute(q, (comment_pk, g.user["user_pk"]))
    row = cursor.fetchone()
    db.close()
    if not row:
        return "not allowed", 403

    html_comment = render_template(
        "___comment.html",
        comment=row,
        post_pk=post_pk,
        user=g.user
    )

    return f"""
        <browser mix-replace="#comment_{comment_pk}">
            {html_comment}
        </browser>
    """


##############################
@app.get("/edit-post/<post_pk>")
@x.no_cache
def edit_post(post_pk):
    try:
        
        # Checks if user is logged in
        if not g.user:
            toast_error = render_template("___toast_error.html", message=x.lans("must_be_logged_in"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 401
        
        # Validate post_pk
        post_pk = x.validate_uuid4_without_dashes(post_pk)
        
        # get post from db
        db, cursor = x.db()
        q = """
            SELECT post_pk, post_message, post_media_path, post_visibility
            FROM posts
            WHERE post_pk = %s AND post_user_fk = %s AND post_deleted_at = 0
        """
        cursor.execute(q, (post_pk, g.user["user_pk"]))
        post = cursor.fetchone()
 
        if not post:
            toast_error = render_template("___toast_error.html", message=x.lans("post_not_found"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 403
        
        edit_post_html = render_template("_edit_post.html", post=post)
        return f'<template mix-replace="#post_container_{post_pk}">{edit_post_html}</template>'
        
    except Exception as ex:
        ic(ex)
        toast_error = render_template("___toast_error.html", message=x.lans("could_not_load_post"))
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
 
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

###############################################

@app.get("/cancel-edit-post/<post_pk>")
def cancel_edit_post(post_pk):
    try:
        if not g.user:
            return "invalid user", 401

        post_pk = x.validate_uuid4_without_dashes(post_pk)

        db, cursor = x.db()

        lan = session["user"]["user_language"]

        # SQL — get the original post without edits
        q = """
            SELECT 
                p.post_pk,
                p.post_user_fk,
                p.post_message,
                p.post_media_path,
                p.post_visibility,
                p.post_total_likes,
                p.post_total_comments,
                p.post_created_at,
                p.post_updated_at,
                p.post_blocked_at,
                p.post_deleted_at,

                u.user_first_name,
                u.user_last_name,
                u.user_username,
                u.user_avatar_path,

                (SELECT COUNT(*) 
                 FROM likes 
                 WHERE like_post_fk = p.post_pk 
                 AND like_user_fk = %s) AS is_liked_by_user

            FROM posts p
            JOIN users u ON u.user_pk = p.post_user_fk
            WHERE p.post_pk = %s AND p.post_user_fk = %s
            LIMIT 1
        """

        cursor.execute(q, (g.user["user_pk"], post_pk, g.user["user_pk"]))
        post = cursor.fetchone()

        if not post:
            return "post_not_found", 404

        # Converte like-count to Boolean
        post["is_liked_by_user"] = post["is_liked_by_user"] > 0

        html_post = render_template("_tweet.html", tweet=post, user=g.user, lan=lan)

        return f"""
        
        <browser mix-replace="#post_container_{post_pk}">{html_post}</browser>
        
        """

    except Exception as ex:
        ic(ex)
        return "error", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

###############################################

@app.route("/api-update-post/<post_pk>", methods=["POST"])
def api_update_post(post_pk):
    try:
        if not g.user: 
            return "invalid user", 400

        post_pk = x.validate_uuid4_without_dashes(post_pk)
        
        post_message = x.validate_post(request.form.get("post_message", ""))
        post_visibility = get_post_visibility_from_form()
        remove_media = request.form.get("remove_media", "0")
        
        db, cursor = x.db()
        
        # Get current post
        cursor.execute("SELECT post_media_path FROM posts WHERE post_pk = %s AND post_user_fk = %s", 
                      (post_pk, g.user["user_pk"]))
        current_post = cursor.fetchone()
        if not current_post:
            return "Post not found", 404
            
        post_media_path = current_post["post_media_path"]
        
        # Handle media removal
        if remove_media == "1" and post_media_path:
            # Delete old file
            old_file = os.path.join('static', post_media_path)
            if os.path.exists(old_file):
                os.remove(old_file)
            post_media_path = ""
        
        # Handle new media upload
        if 'post_media' in request.files:
            file = request.files['post_media']
            if file and file.filename:
                # Delete old file if exists
                if post_media_path:
                    old_file = os.path.join('static', post_media_path)
                    if os.path.exists(old_file):
                        os.remove(old_file)
                
                # Save new file
                file.seek(0, 2)
                size = file.tell()
                file.seek(0)
                
                if size > 5 * 1024 * 1024:  # 5MB
                    raise Exception("x-error file size too large")
                
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                x.validate_image_upload(file, allowed_extensions)
                
                unique_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                
                upload_dir = 'static/images'
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                post_media_path = f"images/{unique_filename}"
        
        # Update database
        q = """UPDATE posts 
               SET post_message = %s, post_media_path = %s, post_visibility = %s, post_updated_at = %s 
               WHERE post_pk = %s AND post_user_fk = %s"""
        cursor.execute(q, (post_message, post_media_path, post_visibility, int(time.time()), post_pk, g.user["user_pk"]))
        db.commit()
        
        # Fetch updated post with user data
        q = """
            SELECT 
                p.*,
                u.user_first_name,
                u.user_last_name,
                u.user_username,
                u.user_avatar_path,
                (
                    SELECT COUNT(*)
                    FROM likes
                    WHERE like_post_fk = p.post_pk
                    AND like_user_fk = %s
                ) AS is_liked_by_user
            FROM posts p
            JOIN users u ON p.post_user_fk = u.user_pk
            WHERE p.post_pk = %s
        """
        cursor.execute(q, (g.user["user_pk"], post_pk))
        updated_post = cursor.fetchone()

        # Convert like count to boolean
        updated_post["is_liked_by_user"] = updated_post["is_liked_by_user"] > 0
        
        toast_ok = render_template("___toast_ok.html", message=x.lans('post_updated'))
        html_post = render_template("_tweet.html", tweet=updated_post, user=g.user)
        
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#post_container_{post_pk}">{html_post}</browser>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): 
            db.rollback()
        
        # File upload errors
        if "x-error file" in str(ex):
            if "size too large" in str(ex):
                toast_error = render_template("___toast_error.html", message=x.lans('image_too_large'))
            else:
                toast_error = render_template("___toast_error.html", message=x.lans('invalid_file_type'))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        
        # Post validation error
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"{x.lans('post')} - {x.POST_MIN_LEN} {x.lans('to')} {x.POST_MAX_LEN} {x.lans('characters')}")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        
        # System error
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
        
    finally:
        if "cursor" in locals(): 
            cursor.close()
        if "db" in locals(): 
            db.close()

##############################
@app.route("/api-update-profile", methods=["POST"])
def api_update_profile():

    try:
        lan = session["user"]["user_language"]
        if not g.user: return "invalid user"

        # Validate
        user_email = x.validate_user_email(lan)
        user_username = x.validate_user_username()
        user_first_name = x.validate_user_first_name()

        # Connect to the database
        q = """
        UPDATE users
        SET user_email = %s,
            user_username = %s,
            user_first_name = %s
        WHERE user_pk = %s
        """


        db, cursor = x.db()
        # Avatar is handled in /api-upload-avatar; pass None to keep current value via COALESCE
        cursor.execute(q, (user_email, user_username, user_first_name, g.user["user_pk"]))
        db.commit()

        # Update session minimally
        session["user"]["user_email"] = user_email
        session["user"]["user_username"] = user_username
        session["user"]["user_first_name"] = user_first_name

        # Response to the browser
      
        toast_ok = render_template("___toast_ok.html", message=x.lans('profile_updated_successfully'))
        nav_html = render_template("___nav_profile_tag.html")
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#profile_tag">{nav_html}</browser>
        """, 200
    except Exception as ex:
        ic(ex)
        # User errors
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        # Database errors
        if "Duplicate entry" and user_email in str(ex): 
            toast_error = render_template("___toast_error.html", message=x.lans('email_already_registered'))
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        if "Duplicate entry" and user_username in str(ex): 
            toast_error = render_template("___toast_error.html", message=x.lans('username_already_registered'))
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        # System or developer error
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
        return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.route("/api-delete-profile", methods=["PUT"])
def api_delete_profile():
    try:
        if not g.user: return "invalid user"

        db, cursor = x.db()
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (int(time.time()), g.user.get("user_pk")))
        db.commit()
        
        session.clear()
        return f"""<browser mix-redirect="{url_for('login')}"></browser>"""

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return "System under maintenance", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/api-upload-avatar", methods=["POST"])
def api_upload_avatar():

# Handles avatar/profile picture upload

    try:
        # Check if user is logged in
        if not g.get("user"):
            raise Exception("You must be logged in", 400)

        # Validate uploaded file
        if "avatar" not in request.files:
            raise Exception("missing file", 400)
        file = request.files["avatar"]
        if not file or not file.filename:
            raise Exception("missing filename", 400)
        allowed_ext = {"jpg", "jpeg", "png", "gif", "webp"}
        try:
            file_extension = x.validate_image_upload(file, allowed_ext)
        except Exception as upload_ex:
            if "x-error file invalid type" in str(upload_ex):
                raise Exception("invalid file type", 400)
            raise

        # Create unique filename with UUID
        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}.{file_extension}"

        # Build filepath inside static/images/avatars
        filepath = os.path.join('static', 'images', 'avatars', filename)

        # Ensure avatars folder exists (absolute on disk)
        avatar_folder = os.path.join(app.root_path, 'static', 'images', 'avatars')
        if not os.path.exists(avatar_folder):
            os.makedirs(avatar_folder)

        # Delete old avatar if it exists (not external URL)
        if g.user.get("user_avatar_path") and not g.user["user_avatar_path"].startswith("http"):
            old_avatar = g.user["user_avatar_path"]  # e.g. static/images/avatars/abc.png
            fs_old = os.path.join(app.root_path, old_avatar.lstrip('/'))
            # Skip deletion of shared default avatars
            is_default = os.path.basename(fs_old) in {"unknown.jpg"}
            if not is_default and os.path.exists(fs_old):
                try:
                    os.remove(fs_old)
                    ic(f"Deleted old avatar: {fs_old}")
                except Exception as e:
                    ic(f"Could not delete old avatar: {e}")

        # Save new file to disk
        file.save(os.path.join(app.root_path, filepath))

        # Update database
        db, cursor = x.db()
        q = "UPDATE users SET user_avatar_path = %s WHERE user_pk = %s"
        cursor.execute(q, (filepath, g.user["user_pk"]))
        db.commit()

        # Update g.user in memory
        g.user["user_avatar_path"] = filepath
        session_user = g.user
        session_user["user_avatar_path"] = filepath
        session["user"] = session_user

        # Send success response and redirect
        toast_ok = render_template("___toast_ok.html", message=x.lans("avatar_updated"))
        nav_html = render_template("___nav_profile_tag.html")
        avatar_url = f"/{filepath}?t={uuid.uuid4().hex}"
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#current_avatar"><img id=\"current_avatar\" src=\"{avatar_url}\" class=\"w-25 h-25 rounded-full obj-f-cover\" alt=\"Current avatar\"></browser>
            <browser mix-replace="#profile_tag">{nav_html}</browser>
        """, 200
    except Exception as ex:
        ic(f"Exception: {ex}")

        # Cleanup: delete uploaded file if error occurred
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)

        # Rollback database changes
        if "db" in locals(): 
            db.rollback()

        # User validation error
        if len(ex.args) > 1 and ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<browser mix-bottom=\"#toast\">{toast_error}</browser>""", 400

        # System error
        toast_error = render_template("___toast_error.html", message=f"{x.lans('could_not_upload_avatar')} {str(ex)}")
        return f"""<browser mix-bottom=\"#toast\">{toast_error}</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/api-search")
def api_search():
    try:
        # Get search input
        search_for = request.form.get("search_for", "").strip()

        if not search_for:
            return """
            <browser mix-replace="#search_results">
                <div id="search_results" class="d-none"></div>
            </browser>
            """
        
        user_pk = g.user["user_pk"]
        part_of_query = f"%{search_for}%"
        
        db, cursor = x.db()
        q = """
            SELECT
                users.user_pk,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path,
                (SELECT COUNT(*) 
                FROM follows 
                WHERE follow_follower_fk = %s 
                AND follow_followed_fk = users.user_pk) AS is_followed_by_user
            FROM users 
            WHERE user_username LIKE %s
            AND user_pk != %s
            AND user_deleted_at = 0
            AND user_blocked_at = 0
            AND user_is_admin = 0
            LIMIT 5
        """
        cursor.execute(q, (user_pk, part_of_query, user_pk))
        users = cursor.fetchall()
        
        if not users:
            users_html = f'<div class="p-2 text-c-gray">{x.lans("user_not_found")}</div>'
        else:
            for u in users:
                u['is_followed_by_user'] = True if u['is_followed_by_user'] > 0 else False
            users_html = render_template("_search_results.html", users=users)

        return f"""
        <browser mix-replace="#search_results">
            <div id="search_results" class="p-absolute top-9 left-0 w-full bg-c-white h-auto pa-4 border-1 border-c-gray:+50 rounded-sm shadow-md">
                {users_html}
            </div>
        </browser>
        """

    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/get-data-from-sheet")
def get_data_from_sheet():
    try:
 
        # Check if the admin is running this end-point, else show error
        admin_user = g.user
        if not admin_user:
            return redirect(url_for("login"))
        if not admin_user.get("user_is_admin"):
            return redirect(url_for("home"))
 
        # flaskwebmail
        # Create a google sheet
        # share and make it visible to "anyone with the link"
        # In the link, find the ID of the sheet. Here: 1aPqzumjNp0BwvKuYPBZwel88UO-OC_c9AEMFVsCw1qU
        # Replace the ID in the 2 places bellow
        url= f"https://docs.google.com/spreadsheets/d/{x.google_spread_sheet_key}/export?format=csv&id={x.google_spread_sheet_key}"
        res=requests.get(url=url)
        # ic(res.text) # contains the csv text structure
        csv_text = res.content.decode('utf-8')
        csv_file = io.StringIO(csv_text) # Use StringIO to treat the string as a file
       
        # Initialize an empty list to store the data
        data = {}
 
        # Read the CSV data
        reader = csv.DictReader(csv_file)
        # ic(reader)
        # Convert each row into the desired structure
        for row in reader:
            item = {
                    'english': row['english'],
                    'danish': row['danish'],
                    'spanish': row['spanish']
               
            }
            # Append the dictionary to the list
            data[row['key']] = (item)
 
        # Convert the data to JSON
        json_data = json.dumps(data, ensure_ascii=False, indent=4)
        # ic(data)
 
        # Save data to the file
        with open("dictionary.json", 'w', encoding='utf-8') as f:
            f.write(json_data)
 
        return "ok"
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        pass
