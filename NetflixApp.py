import time
import os
import re
from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    session as flask_session,
)
from sqlalchemy import (
    create_engine,
    literal,
    or_,
    text,
    func,
    desc,
    func,  # Moved from separate import to here
    distinct,  # Moved from separate import to here
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    sessionmaker,
    aliased,
)  # Consolidated sessionmaker and aliased imports
from flask_mail import Mail, Message
import hashlib
import random

from models import (
    Image,  # Kept as it might be used elsewhere not shown in the snippet
    Movies,
    TVShow,
    TVMoviesCast,
    Cast,
    Genre,
    TVMoviesGenre,
    User,
    TVMoviesCountry,  # Kept as it might be used elsewhere not shown in the snippet
    WatchHistory,
    Session,  # Consolidated Session import
    WatchList,  # Added missing import for WatchList
    MoviesAndTV,
)
from sqlalchemy.sql import text  # Kept as it's used for text queries

Base = declarative_base()

# Change to your database credentials (password, hostname, dbname)
USER = "root"
PASSWORD = ''
HOST = 'localhost'
DBNAME = 'netflix'

DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DBNAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

app = Flask(__name__)

app.secret_key = "your_secret_key"  # Change this to a secure random key

# Example configuration (replace with your actual configuration)
app.config["MAIL_SERVER"] = "smtp.office365.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "netflixdbms@outlook.com"
app.config["MAIL_PASSWORD"] = "Netflixg6"
app.config["MAIL_DEFAULT_SENDER"] = "netflixdbms@outlook.com"
mail = Mail(app)

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  # change to your MongoDB connection
db = client["netflix"]  # Create or use the 'netflix' database
reviews_collection = db["reviews"]  # Create or use the 'reviews' collection
posts_collection = db["posts"]  # Use or create the 'posts' collection
replies_collection = db["replies"]  # Use or create the 'replies' collection

# ================== Dummy Data ==================
# List of users to choose from
users = ["Sam Samson", "Alice Anderson", "Bob Brown", "Charlie Chaplin", "David Doe"]

# Check if the 'reviews' collection exists and if it's empty
if reviews_collection.estimated_document_count() == 0:
    # Dummy data to be inserted
    for i in range(500):
        show_id = str(random.randint(1, 8809))  # Generate show_id once

        dummy_reviews = [
            {
                "_id": ObjectId(),
                "show_id": show_id,
                "user_id": random.choice(users),  # Randomly select a user
                "stars": i % 5 + 1,  # Ratings from 1 to 5
                "liked_by": ["Alice Anderson", "Bob Brown"],
                "review_message": f"This is review {i+1} for show {show_id}.",
                "created_at": datetime.now(),
            }
        ]

        # Insert dummy reviews into the 'reviews' collection
        reviews_collection.insert_many(dummy_reviews)


if posts_collection.estimated_document_count() == 0:
    # Generate dummy data
    for i in range(50):
        # Create a post
        post_data = {
            "_id": ObjectId(),
            "topic_name": f"Discussion {i}",
            "content": f"Post content for discussion {i}.",
            "author_id": random.choice(users),  # Randomly select a user
            "created_at": datetime.now(),
            "replies": [
                {
                    "_id": ObjectId(),
                    "author_id": random.choice(users),  # Randomly select a user
                    "content": f"Immediate reply {i} for discussion {i}.",
                    "created_at": datetime.now(),
                }
            ],
        }

        # Add the post to the 'posts' collection
        posts_collection.insert_one(post_data)

        # Add deeper replies to demonstrate the structure
        if i <= 25:  # Only add deeper replies for the first 25 posts
            for j in range(1, 3):  # Add 2 deeper replies per post
                reply_data = {
                    "_id": ObjectId(),
                    "post_id": post_data["_id"],  # Link to the post
                    "parent_reply_id": post_data["replies"][0][
                        "_id"
                    ],  # Link to the immediate reply
                    "author_id": random.choice(users),  # Randomly select a user
                    "content": f"Deeper reply {j} for discussion {i}.",
                    "created_at": datetime.now(),
                }

                # Add the deeper reply to the 'replies' collection
                replies_collection.insert_one(reply_data)


def md5_hash(text):
    """Helper function to generate MD5 hash."""
    return hashlib.md5(text.encode()).hexdigest()


def execute_sql_script():
    try:
        with open("netflix.sql", "r", encoding="utf-8") as file:
            sql_script = file.read()
    except FileNotFoundError:
        print("Error: The SQL script file 'netflix.sql' was not found.")
        return
    except Exception as e:
        print(f"An error occurred while reading the SQL script: {str(e)[:100]}")
        return

    sql_script = "\n".join(
        line
        for line in sql_script.split("\n")
        if not line.strip().startswith("--") and not line.strip().startswith("/*!")
    )

    statements = re.split(r";\s*\n", sql_script)

    try:
        with engine.connect() as connection:
            for statement in statements:
                statement = statement.strip()
                if statement:
                    connection.execute(
                        text(statement)
                    )  # Use text function to execute SQL statements
        print("Script executed successfully.")
    except Exception as e:
        print(f"An error occurred while executing the SQL script: {str(e)[:900]}")


@app.route("/api/data", methods=["GET"])
def get_data():
    data = {"message": "Hello, this is your data!"}
    return jsonify(data)


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/delete-review/<review_id>", methods=["DELETE"])
def delete_review(review_id):
    try:
        review_id = ObjectId(review_id)
    except Exception as e:
        return str(e), 400

    result = reviews_collection.delete_one({"_id": review_id})

    if result.deleted_count > 0:
        return "", 204  # No content, successful deletion
    else:
        return "Review not found", 404


@app.route("/reviews/<int:showId>/")
def shows_reviews(showId):
    current_user = flask_session.get("username")

    session = Session()
    user = session.query(User).filter_by(username=current_user).first()

    if user and user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string
    print(user.profile_pic)

    movie = (
        session.query(Movies).filter_by(show_id=showId).first()
        or session.query(TVShow).filter_by(show_id=showId).first()
    )

    total_watched = session.query(WatchHistory).filter_by(show_id=showId).count()
    total_likes = (
        session.query(WatchHistory).filter_by(show_id=showId, like_dislike=1).count()
    )
    
    session.close()
    print(total_likes)
    print(total_watched)

    page = request.args.get("page", 1, type=int)
    per_page = 8  # Number of items per page
    skip = (page - 1) * per_page

    items = list(
        reviews_collection.find({"show_id": str(showId)}).skip(skip).limit(per_page)
    )

    total_stars = 0

    for item in items:
        item["total_likes"] = len(item.get("liked_by", []))
        item["status"] = (
            "Liked" if current_user in item.get("liked_by", []) else "noLike"
        )
        total_stars += item.get("stars", 0)

        review_user = (
            session.query(User).filter_by(username=item.get("user_id")).first()
        )
        if review_user:
            item["user_image"] = review_user.profile_pic
            # print(item['user_image'])
        else:
            item["user_image"] = None

    total_items = reviews_collection.count_documents({"show_id": str(showId)})
    avg_stars = round(total_stars / total_items, 2) if total_items > 0 else 0
    max_pages = (total_items // per_page) + (total_items % per_page > 0)
    return render_template(
        "shows-reviews.html",
        user=user,
        username=current_user,
        items=items,
        page=page,
        max_pages=max_pages,
        per_page=per_page,
        movie=movie,
        avg_stars=avg_stars,
        total_likes=total_likes,
        total_watched=total_watched,
        showId=showId,
    )


# all shows review by rating
@app.route("/Allratingby/<int:showId>/<int:rating>")
def all_show_review_rating(showId, rating):
    current_user = flask_session.get("username")

    session = Session()
    user = session.query(User).filter_by(username=current_user).first()

    if user and user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string
    print(user.profile_pic)

    movie = (
        session.query(Movies).filter_by(show_id=showId).first()
        or session.query(TVShow).filter_by(show_id=showId).first()
    )

    total_watched = session.query(WatchHistory).filter_by(show_id=showId).count()
    total_likes = (
        session.query(WatchHistory).filter_by(show_id=showId, like_dislike=1).count()
    )
    
    session.close()
    print(total_likes)
    print(total_watched)

    page = request.args.get("page", 1, type=int)
    per_page = 8  # Number of items per page
    skip = (page - 1) * per_page

    # Fetch reviews and filter by rating
    items = list(
        reviews_collection.find({"show_id": str(showId), "stars": rating})
        .skip(skip)
        .limit(per_page)
    )

    total_stars = 0

    for item in items:
        item["total_likes"] = len(item.get("liked_by", []))
        item["status"] = (
            "Liked" if current_user in item.get("liked_by", []) else "noLike"
        )
        total_stars += item.get("stars", 0)

        review_user = (
            session.query(User).filter_by(username=item.get("user_id")).first()
        )
        if review_user:
            item["user_image"] = review_user.profile_pic
            # print(item['user_image'])
        else:
            item["user_image"] = None

    total_items = reviews_collection.count_documents(
        {"show_id": str(showId), "stars": rating}
    )
    avg_stars = round(total_stars / len(items), 2) if items else 0
    max_pages = (total_items // per_page) + (total_items % per_page > 0)

    return render_template(
        "shows-reviews.html",
        user=user,
        username=current_user,
        items=items,
        page=page,
        max_pages=max_pages,
        per_page=per_page,
        movie=movie,
        avg_stars=avg_stars,
        total_likes=total_likes,
        total_watched=total_watched,
        showId=showId,
    )



# all shows review by date order (asc and desc)
@app.route("/Allorderby/<int:showId>/<string:order>")
def sort_all_reviews_by_date(showId, order):
    current_user = flask_session.get("username")

    session = Session()
    user = session.query(User).filter_by(username=current_user).first()

    if user and user.profile_pic:
        user.profile_pic = "/" + user.profile_pic  # Decode profile_pic from bytes to string
    print(user.profile_pic)

    movie = (
        session.query(Movies).filter_by(show_id=showId).first()
        or session.query(TVShow).filter_by(show_id=showId).first()
    )

    total_watched = session.query(WatchHistory).filter_by(show_id=showId).count()
    total_likes = (
        session.query(WatchHistory).filter_by(show_id=showId, like_dislike=1).count()
    )
    
    session.close()
    
    print(total_likes)
    print(total_watched)

    page = request.args.get("page", 1, type=int)
    per_page = 8  # Number of items per page
    skip = (page - 1) * per_page

    # Fetch reviews
    items = list(
        reviews_collection.find({"show_id": str(showId)})
        .skip(skip)
        .limit(per_page)
    )

    # Sort items based on the order parameter
    if order == "asc":
        items.sort(key=lambda x: x.get("created_at", ""))
    elif order == "desc":
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    total_stars = 0

    for item in items:
        item["total_likes"] = len(item.get("liked_by", []))
        item["status"] = (
            "Liked" if current_user in item.get("liked_by", []) else "noLike"
        )
        total_stars += item.get("stars", 0)

        review_user = (
            session.query(User).filter_by(username=item.get("user_id")).first()
        )
        if review_user:
            item["user_image"] = review_user.profile_pic
            # print(item['user_image'])
        else:
            item["user_image"] = None

    total_items = reviews_collection.count_documents({"show_id": str(showId)})
    avg_stars = round(total_stars / len(items), 2) if items else 0
    max_pages = (total_items // per_page) + (total_items % per_page > 0)

    return render_template(
        "shows-reviews.html",
        user=user,
        username=current_user,
        items=items,
        page=page,
        max_pages=max_pages,
        per_page=per_page,
        movie=movie,
        avg_stars=avg_stars,
        total_likes=total_likes,
        total_watched=total_watched,
        showId=showId,
    )


@app.route("/add-review/<int:showId>", methods=["POST"])
def add_review(showId):
    user_name = flask_session.get("username")
    session = Session()
    referrer = request.form.get("referrer")
    print(referrer)

    # Check if in watch history
    watched = (
        session.query(WatchHistory)
        .filter_by(username=user_name, show_id=showId)
        .first()
    )

    show_name = (session.query(MoviesAndTV).filter_by(id=showId).first()).title

    reviewed = reviews_collection.find_one(
        {"user_id": user_name, "show_id": str(showId)}
    )
    print(reviewed)

    if watched and not reviewed:
        review_message = request.form.get("review")
        stars = request.form.get("ratings")

        reviews_collection.insert_one(
            {
                "show_id": str(showId),
                "user_id": user_name,
                "stars": int(stars),
                "review_message": review_message,
                "created_at": datetime.now(),
                "liked_by": [],
            }
        )

        flash("Review added successfully!", "success")
    elif not watched:
        flash(f"Watch {show_name} before leaving a review.", "error")
    elif watched and reviewed:
        flash("You have reviewed this show already.", "error")

    return redirect(referrer)


@app.route("/edit-review/<review_id>", methods=["POST"])
def edit_review(review_id):
    # Convert review_id from string to ObjectId
    try:
        review_id = ObjectId(review_id)
    except Exception as e:
        # Handle invalid ObjectId
        return str(e), 400

    review_text = request.form.get("review")
    rating = request.form.get("rating-id")
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
    except (ValueError, TypeError) as e:
        # Handle invalid rating
        return str(e), 400

    update_fields = {
        "review_message": review_text,
        "stars": rating,
        "created_at": datetime.now(),
    }

    # Update the review in the database
    result = reviews_collection.update_one(
        {"_id": review_id},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        return "Review not found", 404

    # Redirect or return a response
    return my_reviews()


# allow user to remove like in the mongodb
@app.route("/like-review", methods=["POST"])
def like_review():
    data = request.json
    review_id = data.get("reviewId")

    # Get the current user's username from the session
    current_user = flask_session.get("username")

    if not current_user:
        return jsonify({"success": False, "message": "User not logged in"})

    # Fetch the current review document
    review = reviews_collection.find_one({"_id": ObjectId(review_id)})

    if not review:
        return jsonify({"success": False, "message": "Review not found"})

    liked_by = review.get("liked_by", [])

    if current_user in liked_by:
        # User already liked this review, so we need to remove the like
        result = reviews_collection.update_one(
            {"_id": ObjectId(review_id)}, {"$pull": {"liked_by": current_user}}
        )
        action = "removed"
    else:
        # User has not liked this review, so we need to add the like
        result = reviews_collection.update_one(
            {"_id": ObjectId(review_id)}, {"$addToSet": {"liked_by": current_user}}
        )
        action = "added"

    if result.modified_count > 0:
        return jsonify({"success": True, "action": action})
    else:
        return jsonify({"success": False, "message": "Failed to update review"})


@app.route("/my-reviews")
def my_reviews():
    current_user = flask_session["username"]
    if not current_user:
        return redirect(
            url_for("login")
        )  # Redirect to login if the user is not logged in
        
    session = Session()

    user = session.query(User).filter_by(username=current_user).first()

    if user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )
        
    session.close()

    page = request.args.get("page", 1, type=int)
    per_page = 8  # Number of items per page

    # Fetch reviews and metadata
    items, total_items, max_pages = get_reviews_and_metadata(
        current_user, page, per_page
    )

    return render_template(
        "my-reviews.html",
        user=user,
        username = current_user,
        items=items,
        page=page,
        max_pages=max_pages,
        per_page=per_page,
        total_items=total_items,
    )


# get user's review info
def get_reviews_and_metadata(current_user, page, per_page):
    session = Session()
    skip = (page - 1) * per_page

    # Query to get reviews where user_id matches the current user
    reviews_query = (
        reviews_collection.find({"user_id": current_user}).skip(skip).limit(per_page)
    )
    items = list(reviews_query)

    # Collect show_ids from the reviews
    show_ids = [item.get("show_id") for item in items if item.get("show_id")]

    # Fetch movie/show details based on the show IDs
    movie_info_dict = {}
    if show_ids:
        # Query movies first
        movie_info = (
            session.query(Movies).filter(Movies.show_id.in_(map(int, show_ids))).all()
        )
        movie_info_dict = {movie.show_id: movie for movie in movie_info}

        # Now query TVShows for those show_ids not found in Movies
        missing_show_ids = [
            show_id for show_id in show_ids if show_id not in movie_info_dict
        ]
        if missing_show_ids:
            tv_show_info = (
                session.query(TVShow)
                .filter(TVShow.show_id.in_(map(int, missing_show_ids)))
                .all()
            )
            movie_info_dict.update(
                {tv_show.show_id: tv_show for tv_show in tv_show_info}
            )

    # Format dates, add likes count, and integrate movie/show details
    for item in items:
        show_id = int(item.get("show_id"))  # Convert show_id to int

        movie_or_show = movie_info_dict.get(show_id)

        if movie_or_show:
            item["movie_title"] = getattr(movie_or_show, "title", "Unknown Title")
            item["movie_image"] = getattr(movie_or_show, "image", "default.jpg")
            item["release_year"] = getattr(
                movie_or_show, "release_year", "Unknown Year"
            )
            item["likes_count"] = len(item.get("liked_by", []))
        else:
            item["movie_title"] = "Unknown Title"
            item["movie_image"] = "default.jpg"
            item["release_year"] = "Unknown Year"

    # Count total reviews for pagination
    total_items = reviews_collection.count_documents({"user_id": current_user})
    max_pages = (total_items // per_page) + (total_items % per_page > 0)

    return items, total_items, max_pages


# filter by star rating
@app.route("/ratingBy/<int:rating>")
def rating_by(rating):
    current_user = flask_session.get("username")
    if not current_user:
        return redirect(url_for("login"))
    
    page = request.args.get("page", 1, type=int)
    per_page = 8

    items, total_items, max_pages = get_reviews_and_metadata(
        current_user, page, per_page
    )

    # Filter reviews by rating
    items = [item for item in items if item.get("stars") == rating]

    return render_template(
        "my-reviews.html",
        user=current_user,
        username=current_user,
        items=items,
        page=page,
        max_pages=max_pages,
        per_page=per_page,
        total_items=total_items,
    )


# filter by date
@app.route("/orderby/<string:order>/")
def order_by(order):
    print("order ", order)
    current_user = flask_session.get("username")
    if not current_user:
        return redirect(url_for("login"))
    
    page = request.args.get("page", 1, type=int)
    per_page = 8
    skip = (page - 1) * per_page

    items, total_items, max_pages = get_reviews_and_metadata(
        current_user, page, per_page
    )

    if order == "asc":
        items.sort(key=lambda x: x.get("created_at", ""))
    elif order == "desc":
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return render_template(
        "my-reviews.html",
        user=current_user,
        username=current_user,
        items=items,
        page=page,
        max_pages=max_pages,
        per_page=per_page,
        total_items=total_items,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = md5_hash(password)

        print("Entered password:", password)
        print("Hashed password:", hashed_password)

        db_session = Session()
        user = (
            db_session.query(User)
            .filter_by(username=username, password=hashed_password)
            .first()
        )

        if user:
            # Save user info to Flask session
            flask_session["username"] = user.username
            flask_session["email"] = user.email
            flash("Login successful!", "success")
            print("Saved to Flask session. Username:", flask_session["username"])
            db_session.close()
            return redirect(url_for("homepage", username=username))
        else:
            flash("Login failed. Please check your username and password.", "error")
            db_session.close()
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        profile_pic = request.files.get(
            "profile_pic"
        )  # Assuming the form has a file input for profile pic
        # Check if username already exists
        db_session = Session()
        user_exists = db_session.query(User).filter_by(username=username).first()
        if user_exists:
            flash(
                "Username already exists. Please choose a different username.", "error"
            )
            return redirect(url_for("signup"))

        # Hash the password with MD5 (not recommended for production)
        hashed_password = md5_hash(password)

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            profile_pic=b"",  # Replace with actual profile pic handling
        )
        db_session.add(new_user)
        db_session.commit()

        # Save user info to Flask session
        flask_session["username"] = username
        flask_session["email"] = email
        print("Saved to flask session: Username =", flask_session["username"])

        db_session.close()

        flash("Account created successfully!", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/forget-password", methods=["GET", "POST"])
def forget_password():
    if request.method == "POST":
        email = request.form.get("username")  # Ensure correct form field name

        # Check if the email exists in the database
        db_session = Session()
        user = db_session.query(User).filter_by(email=email).first()

        if user:
            flask_session["email"] = user.email

            # Generate a 4-digit OTP
            otp = "".join([str(random.randint(0, 9)) for _ in range(4)])
            # Store the OTP in the session or database associated with the email
            flask_session["otp"] = otp  #  Store in Flask session
            flask_session["username"] = (
                user.username
            )  # Store the user's ID in the session

            # Send the OTP via email
            msg = Message("Your OTP", recipients=[email])
            msg.body = f"Your OTP is: {otp}"
            mail.send(msg)

            print("OTP sent:", otp)

            db_session.commit()
            db_session.close()
            # Redirect to OTP verification page
            return redirect(url_for("otp"))
        else:
            flash("Email address not found. Please try again.", "error")
            db_session.close()
            return redirect(url_for("forget_password"))

    return render_template("forget-password.html")


@app.route("/otp", methods=["GET", "POST"])
def otp():
    email = flask_session.get("email", "")

    if request.method == "POST":
        otp = (
            request.form.get("otp-1")
            + request.form.get("otp-2")
            + request.form.get("otp-3")
            + request.form.get("otp-4")
        )

        stored_otp = flask_session.get("otp", "")
        username = flask_session.get("username", "")

        print("Entered OTP:", otp, "Stored OTP:", stored_otp)

        # OTP is correct
        if otp == stored_otp:
            flask_session.pop("otp", None)  # Clear the OTP from the session
            return redirect(url_for("reset_password", username=username))
        else:
            flash("Invalid OTP.", "error")
            return redirect(url_for("otp"))
    elif request.method == "GET" and "resend" in request.args:
        # Resend OTP logic here
        email = flask_session.get("email", "")
        if email:
            # Generate a new OTP
            new_otp = "".join([str(random.randint(0, 9)) for _ in range(4)])
            # Store the new OTP in the session
            flask_session["otp"] = new_otp
            # Logic to send the OTP via email
            msg = Message("Your OTP", recipients=[email])
            msg.body = f"Your new OTP is: {new_otp}"
            mail.send(msg)
            flash(
                "New OTP sent successfully! Remember to check your spam folder.", "info"
            )
        else:
            flash("No email found in session. Please log in again.", "warning")

    return render_template("otp.html", email=email)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = flask_session.get("email", "")

    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match. Please try again.", "error")
            return redirect(url_for("reset_password"))

        db_session = Session()
        user = db_session.query(User).filter_by(email=email).first()

        if user:
            # Update the password
            hashed_password = md5_hash(new_password)
            user.password = hashed_password
            # Assuming reset_token is set to None as part of the reset process
            user.reset_token = None
            db_session.commit()
            db_session.close()
            flash("Password reset successful!", "success")

            # Clear session variables related to password reset
            flask_session.pop("email", None)

            return redirect(url_for("login"))
        else:
            flash("User not found. Please try again.", "error")
            db_session.close()
            return redirect(url_for("reset_password"))

    return render_template("reset-password.html", email=email)


@app.route("/profile")
def user_profile():
    current_user = flask_session.get("username")

    session = Session()
    user = session.query(User).filter_by(username=current_user).first()

    if user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string

    watchhistory = session.query(WatchHistory).filter_by(username=current_user).all()
    watchhist_show_ids = [wh.show_id for wh in watchhistory]
    print("cb la fuck", watchhist_show_ids)
    movie_count = (
        session.query(Movies).filter(Movies.show_id.in_(watchhist_show_ids)).count()
    )
    show_count = (
        session.query(TVShow).filter(TVShow.show_id.in_(watchhist_show_ids)).count()
    )
    watched_movies_query = session.query(Movies.show_id, Movies.image).filter(
        Movies.show_id.in_(watchhist_show_ids)
    )

    watched_tvshows_query = session.query(TVShow.show_id, TVShow.image).filter(
        TVShow.show_id.in_(watchhist_show_ids)
    )

    watched_query = watched_movies_query.union_all(watched_tvshows_query).all()

    for show in watched_query:
        print("FUCK", show.show_id)

    movie_hours = (
        session.query(func.sum(Movies.runtime))
        .filter(Movies.show_id.in_(watchhist_show_ids))
        .scalar()
        or 0
    )
    top_genres_id = (
        session.query(
            TVMoviesGenre.genre_id, func.count(TVMoviesGenre.show_id).label("count")
        )
        .filter(TVMoviesGenre.show_id.in_(watchhist_show_ids))
        .group_by(TVMoviesGenre.genre_id)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )
    top_genres = [
        session.query(Genre).filter_by(id=genre_id).first()
        for genre_id, _ in top_genres_id
    ]
    top_actors = (
        session.query(
            Cast.name,  # Select actor name
            func.count(TVMoviesCast.cast_id).label(
                "watch_count"
            ),  # Count the occurrences of each actor
        )
        .join(
            TVMoviesCast,
            TVMoviesCast.cast_id == Cast.id,  # Join Cast to get actor details
        )
        .join(
            WatchHistory,
            WatchHistory.show_id
            == TVMoviesCast.show_id,  # Join WatchHistory to get shows the user has watched
        )
        .filter(WatchHistory.username == current_user)  # Filter by the current user
        .group_by(Cast.id)  # Group by actor to count occurrences
        .order_by(
            func.count(
                TVMoviesCast.cast_id
            ).desc()  # Order by count in descending order
        )
        .limit(5)
        .all()
    )  # Limit to top 5 actors

    session.close()
    user.profile_pic = (
        user.profile_pic if isinstance(user.profile_pic, bytes) else user.profile_pic
    )
    print(user.profile_pic)
    return render_template(
        "user.html",
        username=current_user,
        user=user,
        watchhistory=watchhistory,
        movie_count=movie_count,
        show_count=show_count,
        watched_shows_images=watched_query,
        top_genres=top_genres,
        movie_hours=movie_hours,
        top_actors=top_actors,
    )


# When merge with login. Idk if this works tbh i hope it does.
""" @app.route('/user/<username>')
def user_profile(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()  # Query the database
    session.close()
    return render_template('user.html', user=user)  # Pass data to template """


@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    session = Session()
    user = session.query(User).filter_by(username=flask_session["username"]).first()

    if user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string

    if request.method == "POST":
        # Get form data
        password = request.form.get("password")
        email = request.form.get("email")
        profile_pic = request.files.get("profile_pic")

        # Validate form data here (omitted for brevity)

        # Update user details
        hash_password = md5_hash(password)
        user.password = hash_password
        user.email = email

        # Handle profile picture upload
        profile_pic = request.files.get("profile_pic")
        if profile_pic:
            # Ensure the uploads directory exists
            upload_dir = os.path.join("static", "images")
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # Generate a secure filename for the uploaded file
            filename = secure_filename(profile_pic.filename)
            file_path = os.path.join(upload_dir, filename)

            # Save the file
            profile_pic.save(file_path)
            # Update the user's profile_pic field with the file path
            user.profile_pic = file_path.replace("\\", "/")

            print(filename)
        # Commit changes to database
        session.commit()

        # Redirect to profile page
        session.close()
        return redirect(url_for("user_profile"))

    # Render edit profile page
    return render_template("edit_profile.html", user=user)


@app.route("/watchlist")
def watchlist():
    logged_in_username = flask_session["username"]

    db_session = Session()

    user = db_session.query(User).filter_by(username=logged_in_username).first()

    if user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string

    # Query for all show images in watchlist
    posters = db_session.execute(
        text(
            """
        SELECT
            COALESCE(m.image, t.image) AS image,
            GROUP_CONCAT(DISTINCT g.name ORDER BY g.name SEPARATOR ', ') AS genre,
            COALESCE(m.show_id, t.show_id) AS show_id,
            COALESCE(m.title, t.title) AS title
        FROM
            watchlist w
        LEFT JOIN
            movies m ON w.show_id = m.show_id
        LEFT JOIN
            tv_shows t ON w.show_id = t.show_id
        LEFT JOIN
            tv_movies_genre tg ON tg.show_id = w.show_id
        LEFT JOIN
            genre g ON tg.genre_id = g.id
        WHERE
            w.username = :username
        GROUP BY
            COALESCE(m.show_id, t.show_id);
    """
        ),
        {"username": logged_in_username},
    ).fetchall()

    for poster in posters:
        print(poster)

    # Query for distinct genres in watchlist
    genre_alias = aliased(Genre)
    query = (
        db_session.query(distinct(genre_alias.name).label("name"))
        .outerjoin(TVMoviesGenre, genre_alias.id == TVMoviesGenre.genre_id)
        .outerjoin(WatchList, TVMoviesGenre.show_id == WatchList.show_id)
        .filter(WatchList.username == logged_in_username)
    )

    # poster_results = posters.all()
    results = query.all()

    db_session.close()

    return render_template(
        "watchlist.html",
        posters=posters,
        genres=[result.name for result in results],
        username=logged_in_username,
        user=user,
    )


@app.route("/add-to-watchlist", methods=["POST"])
def add_to_watchlist():
    if request.method == "POST":
        username = flask_session.get("username")
        show_id = request.form.get("show_id")

        db_session = Session()

        # Check if the show is already in the watchlist
        watchlist_exists = (
            db_session.query(WatchList)
            .filter_by(username=username, show_id=show_id)
            .first()
        )

        if watchlist_exists:
            flash("Show is already in your watchlist.", "exist")
            db_session.close()
            return redirect(request.referrer or url_for("watchlist"))
        else:
            # Create a new watchlist entry
            new_watchlist = WatchList(username=username, show_id=show_id, watched=0)
            flash("Show added to watchlist!", "success")

            db_session.add(new_watchlist)
            db_session.commit()
            db_session.close()

        # After adding to watchlist, redirect back to the referring page or a default page
        return redirect(request.referrer or url_for("watchlist"))


@app.route("/remove-from-watchlist", methods=["POST"])
def remove_from_watchlist():
    if request.method == "POST":
        username = flask_session.get("username")
        show_id = request.form.get("show_id")

        db_session = Session()

        # Check if the show is in the watchlist
        show_exists = (
            db_session.query(WatchList)
            .filter_by(username=username, show_id=show_id)
            .first()
        )
        print(show_exists)

        if show_exists:
            db_session.delete(show_exists)
            db_session.commit()
            flash("Show removed from watchlist!", "success")
            db_session.close()
        else:
            flash("Show is not in your watchlist.", "error")
            db_session.close()

        # After removing from watchlist, redirect back to the referring page or a default page
        return redirect(request.referrer or url_for("watchlist"))


@app.route("/watch-history")
def watch_history():
    logged_in_username = flask_session["username"]

    db_session = Session()

    user = db_session.query(User).filter_by(username=logged_in_username).first()
    if user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string

    # Query for all show images in watch history
    posters = db_session.execute(
        text(
            """
        SELECT
            COALESCE(m.image, t.image) AS image,
            GROUP_CONCAT(DISTINCT g.name ORDER BY g.name SEPARATOR ', ') AS genre,
            COALESCE(m.show_id, t.show_id) AS show_id,
            COALESCE(m.title, t.title) AS title
        FROM
            watchhistory w
        LEFT JOIN
            movies m ON w.show_id = m.show_id
        LEFT JOIN
            tv_shows t ON w.show_id = t.show_id
        LEFT JOIN
            tv_movies_genre tg ON tg.show_id = w.show_id
        LEFT JOIN
            genre g ON tg.genre_id = g.id
        WHERE
            w.username = :username
        GROUP BY
            COALESCE(m.show_id, t.show_id);
    """
        ),
        {"username": logged_in_username},
    ).fetchall()

    for poster in posters:
        print(poster)

    # Query for distinct genres in watch history
    genre_alias = aliased(Genre)
    query = (
        db_session.query(distinct(genre_alias.name).label("name"))
        .outerjoin(TVMoviesGenre, genre_alias.id == TVMoviesGenre.genre_id)
        .outerjoin(WatchHistory, TVMoviesGenre.show_id == WatchHistory.show_id)
        .filter(WatchHistory.username == logged_in_username)
    )

    # poster_results = posters.all()
    results = query.all()

    db_session.close()

    return render_template(
        "watchhistory.html",
        posters=posters,
        genres=[result.name for result in results],
        username=logged_in_username,
        user=user,
    )


@app.route("/add-to-watchhistory", methods=["POST"])
def add_to_watchhistory():
    if request.method == "POST":
        username = flask_session.get("username")
        show_id = request.form.get("show_id")

        db_session = Session()

        # Check if the show is already in the watchlist
        show_exists = (
            db_session.query(WatchHistory)
            .filter_by(username=username, show_id=show_id)
            .first()
        )

        if show_exists:
            flash("Show is already in your watch history.", "exist")
            db_session.close()
            return redirect(request.referrer or url_for("watch_history"))
        else:
            # Create a new watchlist entry
            new_watchHistory = WatchHistory(username=username, show_id=show_id)
            flash("Show added to watch history!", "success")

            db_session.add(new_watchHistory)
            db_session.commit()
            db_session.close()

        # After adding to watchlist, redirect back to the referring page or a default page
        return redirect(request.referrer or url_for("watch_history"))


@app.route("/remove-from-watchhistory", methods=["POST"])
def remove_from_watchhistory():
    username = flask_session.get("username")
    show_id = request.form.get("show_id")

    db_session = Session()

    show_exists = (
        db_session.query(WatchHistory)
        .filter_by(username=username, show_id=show_id)
        .first()
    )

    if show_exists:
        db_session.delete(show_exists)
        db_session.commit()
        flash("Show removed from watch history!", "success")
        db_session.close()
    else:
        flash("Show is not in your watch history.", "error")
        db_session.close()

    return redirect(request.referrer or url_for("watch_history"))


@app.route("/add-rating", methods=["POST"])
def rate():
    if request.method == "POST":
        username = flask_session.get("username")
        show_id = request.form.get("show_id")
        rating = request.form.get("rating")

        if rating == "like":
            rating_bool = True
        else:
            rating_bool = False

        db_session = Session()

        # Check if the show is already in the watchlist
        show_exists = (
            db_session.query(WatchHistory)
            .filter_by(username=username, show_id=show_id)
            .first()
        )

        if show_exists:
            show_exists.like_dislike = rating_bool
            db_session.commit()
            db_session.close()
            return redirect(request.referrer or url_for("watchlist"))
        else:
            flash("Watch it before rating :(", "error")
            db_session.close()
            return redirect(request.referrer or url_for("watchlist"))


""" including cast in search takes a long time to query, exclude for now"""


@app.route("/search")
def search():
    starttime = time.time()
    current_user = flask_session.get("username")

    db_session = Session()

    user = db_session.query(User).filter_by(username=current_user).first()

    search_query = request.args.get("q")  # Get search query

    # Combined query for Movies and TV Shows based on title or genre
    combined_query = (
        db_session.query(
            Movies.show_id,
            Movies.title,
            Movies.image,
            Genre.name.label("genre"),
            literal("movie").label("type"),
        )
        .join(TVMoviesGenre, Movies.show_id == TVMoviesGenre.show_id)
        .join(Genre, TVMoviesGenre.genre_id == Genre.id)
        .filter(
            or_(
                Movies.title.like(f"%{search_query}%"),
                Genre.name.like(f"%{search_query}%"),
            )
        )
        .union_all(
            db_session.query(
                TVShow.show_id,
                TVShow.title,
                TVShow.image,
                Genre.name.label("genre"),
                literal("tvshow").label("type"),
            )
            .join(TVMoviesGenre, TVShow.show_id == TVMoviesGenre.show_id)
            .join(Genre, TVMoviesGenre.genre_id == Genre.id)
            .filter(
                or_(
                    TVShow.title.like(f"%{search_query}%"),
                    Genre.name.like(f"%{search_query}%"),
                )
            )
        )
    )

    db_session.close()

    # Execute the combined query and fetch results
    combined_results = combined_query.all()

    # Process results to remove duplicates and prepare for rendering
    unique_results = {}
    for result in combined_results:
        key = (result.title, result.type)
        if key not in unique_results:
            unique_results[key] = {
                "show_id": result.show_id,
                "type": result.type,
                "title": result.title,
                "image": result.image,
            }

    formatted_results = list(unique_results.values())

    endtime = time.time()
    print(f"Time taken: {endtime - starttime:.2f} seconds")

    return render_template(
        "search.html",
        results=formatted_results,
        search_query=search_query,
        username=current_user,
        user=user,
    )


@app.route("/details/<int:tv_movie_id>")
def show_details(tv_movie_id):
    current_user = flask_session.get("username")

    session = Session()
    user = session.query(User).filter_by(username=current_user).first()

    if user and user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string

    movie = (
        session.query(Movies).filter_by(show_id=tv_movie_id).first()
        or session.query(TVShow).filter_by(show_id=tv_movie_id).first()
    )

    cast = (
        session.query(Cast.name)
        .join(TVMoviesCast, Cast.id == TVMoviesCast.cast_id)
        .filter((TVMoviesCast.show_id) == tv_movie_id)
        .all()
    )
    cast_names = [name for name, in cast]
    genre = (
        session.query(Genre.name)
        .join(TVMoviesGenre, Genre.id == TVMoviesGenre.genre_id)
        .filter((TVMoviesGenre.show_id) == tv_movie_id)
        .all()
    )
    genre_names = [name for name, in genre]
    watch_history = (
        session.query(WatchHistory)
        .filter_by(username=current_user, show_id=tv_movie_id)
        .first()
    )

    # Initialized to None for shows with no reviews
    popular_review = None
    recent_review = None

    # Pipeline to query popular review based on most likes
    pipeline = [
        {"$match": {"show_id": str(tv_movie_id)}},  # Filter by show_id
        {
            "$addFields": {"liked_by_count": {"$size": "$liked_by"}}
        },  # Add a field for the length of the liked_by array
        {"$sort": {"liked_by_count": -1}},  # Sort by the new field in descending order
        {"$limit": 3},  # Limit to 1 document
    ]

    top_review = list(reviews_collection.aggregate(pipeline))

    top_reviews = []

    for review in top_review:
        review_obj = review
        review_obj["like_count"] = len(review.get("liked_by", []))
        top_user = session.query(User).filter_by(username=review.get("user_id")).first()
        if top_user:
            review_obj["profile_pic"] = top_user.profile_pic
        else:
            review_obj["profile_pic"] = None

        # Check if current_user is in the liked_by array
        if current_user in review.get("liked_by", []):
            review_obj["status"] = "Liked"
        else:
            review_obj["status"] = "noLike"
            
        top_reviews.append(review_obj)

    # Query for the 3 most recent reviews
    latest_reviews = list(
        reviews_collection.find({"show_id": str(tv_movie_id)})
        .sort("created_at", DESCENDING)
        .limit(3)
    )

    recent_reviews = []

    for review in latest_reviews:
        review_obj = review
        review_obj["like_count"] = len(review.get("liked_by", []))
        recent_user = session.query(User).filter_by(username=review.get("user_id")).first()
        if recent_user:
            review_obj["profile_pic"] = recent_user.profile_pic
        else:
            review_obj["profile_pic"] = None

        # Check if current_user is in the liked_by array
        if current_user in review.get("liked_by", []):
            review_obj["status"] = "Liked"
        else:
            review_obj["status"] = "noLike"
        
        recent_reviews.append(review_obj)

    items = list(reviews_collection.find({"show_id": str(tv_movie_id)}))
    total_stars = 0

    for item in items:
        total_stars += item.get("stars", 0)

    total_items = reviews_collection.count_documents({"show_id": str(tv_movie_id)})
    avg_stars = round(total_stars / total_items, 2) if total_items > 0 else 0

    query1 = [
        {"$match": {"show_id": str(tv_movie_id)}},
        {"$group": {"_id": "$stars", "count": {"$sum": 1}}},
        {"$match": {"_id": {"$in": [1, 2, 3, 4, 5]}}},  # Filter for stars 1 to 5
        {"$sort": {"_id": 1}},
    ]

    stars_count = list(reviews_collection.aggregate(query1))
    star_counts = {i: 0 for i in range(1, 6)}
    # Populate the dictionary with counts from the aggregation
    for star in stars_count:
        star_counts[star["_id"]] = star["count"]

    session.close()
    return render_template(
        "movie-series-details.html",
        username=current_user,
        user=user,
        movie=movie,
        cast_names=cast_names,
        genre_names=genre_names,
        watch_history=watch_history,
        popular_reviews=top_reviews,
        recent_reviews=recent_reviews,
        total_items=total_items,
        avg_stars=avg_stars,
        star_counts=star_counts,
    )


@app.route("/content/<string:username>/")
def series_movies(username):
    session = Session()

    limit = 10

    user = session.query(User).filter_by(username=username).first()

    if user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string

    liked_genre_movies = []
    liked_genre_tv = []
    liked_cast_movie = []
    liked_cast_tv = []
    liked_countries_movies = []
    liked_countries_tvshows = []
    herosmovie = []
    movie_data = []
    tv_data = []
    watch_history = []

    has_watch_history = session.query(WatchHistory).filter_by(username=username).first()
    # print(has_watch_history)
    if has_watch_history:

        try:

            # Liked Genre Movies

            top_genre = (
                session.query(TVMoviesGenre.genre_id)
                .join(WatchHistory, WatchHistory.show_id == TVMoviesGenre.show_id)
                .filter(WatchHistory.username == username)
                .filter(WatchHistory.like_dislike == 1)
                .group_by(TVMoviesGenre.genre_id)
                .order_by(func.count(WatchHistory.show_id).desc())
                .first()[0]
            )

            other_movies_by_genre = (
                session.query(TVMoviesGenre.show_id)
                .filter(TVMoviesGenre.genre_id == top_genre)
                .limit(limit)
                .all()
            )
            other_movie_ids = [movie[0] for movie in other_movies_by_genre]

            movies = (
                session.query(
                    Movies.image,
                    Movies.show_id,
                    Movies.title,
                    Movies.runtime,
                    Movies.rating,
                    Movies.release_year,
                    Movies.description,
                )
                .filter(Movies.show_id.in_(other_movie_ids))
                .all()
            )

            liked_genre_movies = []
            for (
                image,
                show_id,
                title,
                runtime,
                rating,
                release_year,
                description,
            ) in movies:
                liked_genre_movies.append(
                    {
                        "image_url": image,
                        "show_id": show_id,
                        "title": title,
                        "runtime": runtime,
                        "rating": rating,
                        "release_year": release_year,
                        "description": description,
                    }
                )

            # Liked Genre TV Shows

            top_genre = (
                session.query(TVMoviesGenre.genre_id)
                .join(WatchHistory, WatchHistory.show_id == TVMoviesGenre.show_id)
                .filter(WatchHistory.username == username)
                .filter(WatchHistory.like_dislike == 1)
                .group_by(TVMoviesGenre.genre_id)
                .order_by(func.count(WatchHistory.show_id).desc())
                .first()[0]
            )

            other_tvshow_by_genre = (
                session.query(TVMoviesGenre.show_id)
                .filter(TVMoviesGenre.genre_id == top_genre)
                .limit(limit)
                .all()
            )
            other_tvshow_ids = [tv[0] for tv in other_tvshow_by_genre]

            tvs = (
                session.query(
                    TVShow.image,
                    TVShow.show_id,
                    TVShow.title,
                    TVShow.season,
                    TVShow.rating,
                    TVShow.release_year,
                    TVShow.description,
                )
                .filter(TVShow.show_id.in_(other_tvshow_ids))
                .all()
            )

            liked_genre_tv = []
            for image, show_id, title, season, rating, release_year, description in tvs:
                liked_genre_tv.append(
                    {
                        "image_url": image,
                        "show_id": show_id,
                        "title": title,
                        "season": season,
                        "rating": rating,
                        "release_year": release_year,
                        "description": description,
                    }
                )

            # Movies with most watched actor

            top_actor = (
                session.query(TVMoviesCast.cast_id)
                .join(WatchHistory, WatchHistory.show_id == TVMoviesCast.show_id)
                .filter(WatchHistory.username == username)
                .filter(WatchHistory.like_dislike == 1)
                .group_by(TVMoviesCast.cast_id)
                .order_by(func.count(WatchHistory.show_id).desc())
                .first()[0]
            )

            other_movies_by_actor = (
                session.query(TVMoviesCast.show_id)
                .filter(TVMoviesCast.cast_id == top_actor)
                .limit(limit)
                .all()
            )
            other_movie_ids = [movie[0] for movie in other_movies_by_actor]

            movies = (
                session.query(
                    Movies.image,
                    Movies.show_id,
                    Movies.title,
                    Movies.runtime,
                    Movies.rating,
                    Movies.release_year,
                    Movies.description,
                )
                .filter(Movies.show_id.in_(other_movie_ids))
                .all()
            )

            liked_cast_movie = []

            for (
                image,
                show_id,
                title,
                runtime,
                rating,
                release_year,
                description,
            ) in movies:
                liked_cast_movie.append(
                    {
                        "image_url": image,
                        "show_id": show_id,
                        "title": title,
                        "runtime": runtime,
                        "rating": rating,
                        "release_year": release_year,
                        "description": description,
                    }
                )

            # TV Shows with most watched actor

            top_actor = (
                session.query(TVMoviesCast.cast_id)
                .join(WatchHistory, WatchHistory.show_id == TVMoviesCast.show_id)
                .filter(WatchHistory.username == username)
                .filter(WatchHistory.like_dislike == 1)
                .group_by(TVMoviesCast.cast_id)
                .order_by(func.count(WatchHistory.show_id).desc())
                .first()[0]
            )
            # print(top_actor)

            other_tvshow_by_actor = (
                session.query(TVMoviesCast.show_id)
                .filter(TVMoviesCast.cast_id == top_actor)
                .limit(limit)
                .all()
            )

            other_tvshow_ids = [tv[0] for tv in other_tvshow_by_actor]
            # print(other_tvshow_ids)

            tvs = (
                session.query(
                    TVShow.image,
                    TVShow.show_id,
                    TVShow.title,
                    TVShow.season,
                    TVShow.rating,
                    TVShow.release_year,
                    TVShow.description,
                )
                .filter(TVShow.show_id.in_(other_tvshow_ids))
                .all()
            )

            liked_cast_tv = []

            for image, show_id, title, season, rating, release_year, description in tvs:
                liked_cast_tv.append(
                    {
                        "image_url": image,
                        "show_id": show_id,
                        "title": title,
                        "season": season,
                        "rating": rating,
                        "release_year": release_year,
                        "description": description,
                    }
                )

            # Movies From Around The Globe

            top_country = (
                session.query(TVMoviesCountry.country_id)
                .join(WatchHistory, WatchHistory.show_id == TVMoviesCountry.show_id)
                .filter(WatchHistory.username == username)
                .filter(WatchHistory.like_dislike == 1)
                .group_by(TVMoviesCountry.country_id)
                .order_by(func.count(WatchHistory.show_id).desc())
                .first()[0]
            )
            # print(top_country)

            other_movies_by_country = (
                session.query(TVMoviesCountry.show_id)
                .filter(TVMoviesCountry.country_id == top_country)
                .limit(limit)
                .all()
            )
            other_movie_ids = [movie[0] for movie in other_movies_by_country]

            movies = (
                session.query(
                    Movies.image,
                    Movies.show_id,
                    Movies.title,
                    Movies.runtime,
                    Movies.rating,
                    Movies.release_year,
                    Movies.description,
                )
                .filter(Movies.show_id.in_(other_movie_ids))
                .all()
            )

            liked_countries_movies = []
            for (
                image,
                show_id,
                title,
                runtime,
                rating,
                release_year,
                description,
            ) in movies:
                liked_countries_movies.append(
                    {
                        "image_url": image,
                        "show_id": show_id,
                        "title": title,
                        "runtime": runtime,
                        "rating": rating,
                        "release_year": release_year,
                        "description": description,
                    }
                )

            # TV Shows From Around The Globe

            top_country = (
                session.query(TVMoviesCountry.country_id)
                .join(WatchHistory, WatchHistory.show_id == TVMoviesCountry.show_id)
                .filter(WatchHistory.username == username)
                .filter(WatchHistory.like_dislike == 1)
                .group_by(TVMoviesCountry.country_id)
                .order_by(func.count(WatchHistory.show_id).desc())
                .first()[0]
            )
            # print(top_country)

            other_tvshow_by_country = (
                session.query(TVMoviesCountry.show_id)
                .filter(TVMoviesCountry.country_id == top_country)
                .limit(limit)
                .all()
            )
            other_tvshow_ids = [tv[0] for tv in other_tvshow_by_country]

            tvs = (
                session.query(
                    TVShow.image,
                    TVShow.show_id,
                    TVShow.title,
                    TVShow.season,
                    TVShow.rating,
                    TVShow.release_year,
                    TVShow.description,
                )
                .filter(TVShow.show_id.in_(other_tvshow_ids))
                .all()
            )

            liked_countries_tvshows = []
            for image, show_id, title, season, rating, release_year, description in tvs:
                liked_countries_tvshows.append(
                    {
                        "image_url": image,
                        "show_id": show_id,
                        "title": title,
                        "season": season,
                        "rating": rating,
                        "release_year": release_year,
                        "description": description,
                    }
                )
        except Exception as e:
            print(f"Error occurred: {e}")

    checkEmpty = session.query(WatchHistory).first()
    # print(checkEmpty)

    if checkEmpty:  # Checks if WatchHistory is empty, needed for most popular

        # Most liked movies across all users

        most_liked_movies_query = (
            session.query(
                Movies.show_id,
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                func.count(WatchHistory.show_id).label("like_count"),
                Movies.image,
            )
            .join(WatchHistory, WatchHistory.show_id == Movies.show_id)
            .filter(WatchHistory.like_dislike == 1)
            .group_by(
                Movies.show_id,
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                Movies.image,
            )
            .order_by(desc(func.count(WatchHistory.show_id)))
            .limit(limit)
            .all()
        )

        movie_data = []
        for (
            show_id,
            title,
            runtime,
            rating,
            release_year,
            description,
            like_count,
            image,
        ) in most_liked_movies_query:
            movie_data.append(
                {
                    "show_id": show_id,
                    "title": title,
                    "runtime": runtime,
                    "rating": rating,
                    "release_year": release_year,
                    "description": description,
                    "like_count": like_count,
                    "image_url": image,
                }
            )

            # Most liked tv shows across all users
        most_liked_tv_query = (
            session.query(
                TVShow.show_id,
                TVShow.title,
                TVShow.season,
                TVShow.rating,
                TVShow.release_year,
                TVShow.description,
                func.count(WatchHistory.show_id).label("like_count"),
                TVShow.image,
            )
            .join(WatchHistory, WatchHistory.show_id == TVShow.show_id)
            .filter(WatchHistory.like_dislike == 1)
            .group_by(
                TVShow.show_id,
                TVShow.title,
                TVShow.season,
                TVShow.rating,
                TVShow.release_year,
                TVShow.description,
                TVShow.image,
            )
            .order_by(desc(func.count(WatchHistory.show_id)))
            .limit(limit)
            .all()
        )

        tv_data = []
        for (
            show_id,
            title,
            season,
            rating,
            release_year,
            description,
            like_count,
            image,
        ) in most_liked_tv_query:
            tv_data.append(
                {
                    "show_id": show_id,
                    "title": title,
                    "season": season,
                    "rating": rating,
                    "release_year": release_year,
                    "description": description,
                    "like_count": like_count,
                    "image_url": image,
                }
            )

            # Hero Section
        hero_movie_query = (
            session.query(
                Movies.show_id,
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                func.count(WatchHistory.show_id).label("like_count"),
                Movies.image,
            )
            .join(WatchHistory, WatchHistory.show_id == Movies.show_id)
            .filter(WatchHistory.like_dislike == 1)
            .group_by(
                Movies.show_id,
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                Movies.image,
            )
            .order_by(desc(func.count(WatchHistory.show_id)))
            .limit(1)
            .all()
        )

        herosmovie = []
        for (
            show_id,
            title,
            runtime,
            rating,
            release_year,
            description,
            like_count,
            image,
        ) in hero_movie_query:
            herosmovie.append(
                {
                    "show_id": show_id,
                    "title": title,
                    "runtime": runtime,
                    "rating": rating,
                    "release_year": release_year,
                    "description": description,
                    "like_count": like_count,
                    "image_url": image,
                }
            )

        # get rating detail of hero movie
        watch_history = (
            session.query(WatchHistory)
            .filter_by(username=username, show_id=herosmovie[0]["show_id"])
            .first()
        )

    # Originals will always display regardless of whether watchhistory is empty or not.

    # Originals Movies (Random)

    originals_movies_query = (
        session.query(
            Movies.show_id,
            Movies.title,
            Movies.runtime,
            Movies.rating,
            Movies.release_year,
            Movies.description,
            Movies.image,
        )
        .order_by(func.random())
        .limit(limit)
        .all()
    )

    originals_movies = []
    for (
        show_id,
        title,
        runtime,
        rating,
        release_year,
        description,
        image,
    ) in originals_movies_query:
        originals_movies.append(
            {
                "show_id": show_id,
                "title": title,
                "runtime": runtime,
                "rating": rating,
                "release_year": release_year,
                "description": description,
                "image_url": image,
            }
        )

    # Originals TV Shows (Random)

    originals_tv_query = (
        session.query(
            TVShow.show_id,
            TVShow.title,
            TVShow.season,
            TVShow.rating,
            TVShow.release_year,
            TVShow.description,
            TVShow.image,
        )
        .order_by(func.random())
        .limit(limit)
        .all()
    )

    originals_tv = []
    for (
        show_id,
        title,
        season,
        rating,
        release_year,
        description,
        image,
    ) in originals_tv_query:
        originals_tv.append(
            {
                "show_id": show_id,
                "title": title,
                "season": season,
                "rating": rating,
                "release_year": release_year,
                "description": description,
                "image_url": image,
            }
        )

    user = session.query(User).filter_by(username=username).first()
    # print("fuck u why not displaying??",user.profile_pic)

    session.close()

    return render_template(
        "series-movies.html",
        herosmovie=herosmovie,
        username=username,
        liked_cast_movie=liked_cast_movie,
        liked_cast_tv=liked_cast_tv,
        movie_data=movie_data,
        tv_data=tv_data,
        originals_movies=originals_movies,
        originals_tv=originals_tv,
        liked_countries_movies=liked_countries_movies,
        liked_countries_tvshows=liked_countries_tvshows,
        liked_genre_movies=liked_genre_movies,
        liked_genre_tv=liked_genre_tv,
        watch_history=watch_history,
        user=user,
    )


# Assuming you have models defined for WatchHistory, TVMoviesCountry, Movies, etc.
# Make sure to define your models according to your database schema


@app.route("/homepage/<string:username>/")
def homepage(username):
    session = Session()
    limit = 6
    user = session.query(User).filter_by(username=username).first()

    if user.profile_pic:
        user.profile_pic = (
            "/" + user.profile_pic
        )  # Decode profile_pic from bytes to string

    print("fucker", user.profile_pic)

    try:
        # Hero Section
        hero_movie = (
            session.query(
                Movies.show_id,
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                func.count(WatchHistory.show_id).label("like_count"),
                Movies.image,
            )
            .join(WatchHistory, WatchHistory.show_id == Movies.show_id)
            .filter(WatchHistory.like_dislike == 1)
            .group_by(
                Movies.show_id,
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                Movies.image,
            )
            .order_by(desc(func.count(WatchHistory.show_id)))
            .limit(1)
            .all()
        )

        herosmovie = []
        for (
            show_id,
            title,
            runtime,
            rating,
            release_year,
            description,
            like_count,
            image,
        ) in hero_movie:
            herosmovie.append(
                {
                    "show_id": show_id,
                    "title": title,
                    "runtime": runtime,
                    "rating": rating,
                    "release_year": release_year,
                    "description": description,
                    "like_count": like_count,
                    "image_url": image,
                }
            )

        # Query to find if the user has liked any content
        has_liked_content = (
            session.query(WatchHistory.show_id)
            .filter(WatchHistory.username == username, WatchHistory.like_dislike == 1)
            .first()
            is not None
        )

        # Query to find the last liked show ID for the user
        last_liked_show_id_query = (
            session.query(WatchHistory.show_id)
            .filter(WatchHistory.username == username, WatchHistory.like_dislike == 1)
            .order_by(desc(WatchHistory.show_id))
            .first()
        )

        last_liked_show_id = (
            last_liked_show_id_query.show_id if last_liked_show_id_query else None
        )

        # Query to find the most liked genre by counting occurrences where the user liked the show
        liked_genre_query = (
            session.query(
                TVMoviesGenre.genre_id,
                func.count(TVMoviesGenre.genre_id).label("genre_count"),
            )
            .join(WatchHistory, TVMoviesGenre.show_id == WatchHistory.show_id)
            .filter(WatchHistory.username == username, WatchHistory.like_dislike == 1)
            .group_by(TVMoviesGenre.genre_id)
            .order_by(desc(func.count(TVMoviesGenre.genre_id)))
            .first()
        )

        liked_genre_id = liked_genre_query.genre_id if liked_genre_query else None

        # Fetch the countries from the user's watch history
        watched_countries_query = (
            session.query(TVMoviesCountry.country_id)
            .join(WatchHistory, TVMoviesCountry.show_id == WatchHistory.show_id)
            .filter(WatchHistory.username == username, WatchHistory.like_dislike == 1)
            .distinct()
        )

        watched_countries = [country.country_id for country in watched_countries_query]

        # Separate queries for movies and TV shows excluding the last liked show and based on liked genre
        movies_query = (
            session.query(
                Movies.show_id.label("show_id"),
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                Movies.image,
                TVMoviesGenre.genre_id,  # Include genre_id to filter similar movies
            )
            .join(TVMoviesGenre, Movies.show_id == TVMoviesGenre.show_id)
            .filter(
                TVMoviesGenre.genre_id == liked_genre_id,
                Movies.show_id != last_liked_show_id if last_liked_show_id else True,
            )
            .distinct()
            .limit(limit // 2)
        )

        tvshows_query = (
            session.query(
                TVShow.show_id.label("show_id"),
                TVShow.title,
                TVShow.season.label(
                    "runtime"
                ),  # Use 'season' as 'runtime' for TV shows
                TVShow.rating,
                TVShow.release_year,
                TVShow.description,
                TVShow.image,
                TVMoviesGenre.genre_id,  # Include genre_id to filter similar TV shows
            )
            .join(TVMoviesGenre, TVShow.show_id == TVMoviesGenre.show_id)
            .filter(
                TVMoviesGenre.genre_id == liked_genre_id,
                TVShow.show_id != last_liked_show_id if last_liked_show_id else True,
            )
            .distinct()
            .limit(limit - limit // 2)
        )

        # Execute the queries and process the results
        movies_results = movies_query.all()
        tvshows_results = tvshows_query.all()

        # Combine movies and TV shows into separate lists of dictionaries
        similar_genre_movies = []
        for row in movies_results:
            similar_genre_movies.append(
                {
                    "show_id": row.show_id,
                    "title": row.title,
                    "runtime": row.runtime,
                    "rating": row.rating,
                    "release_year": row.release_year,
                    "description": row.description,
                    "image_url": row.image,
                }
            )

        for row in tvshows_results:
            similar_genre_movies.append(
                {
                    "show_id": row.show_id,
                    "title": row.title,
                    "runtime": row.runtime,
                    "rating": row.rating,
                    "release_year": row.release_year,
                    "description": row.description,
                    "image_url": row.image,
                }
            )

        # Query for similar country movies
        similar_country_movies_query = (
            session.query(
                Movies.show_id.label("show_id"),
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                Movies.image,
            )
            .join(TVMoviesCountry, Movies.show_id == TVMoviesCountry.show_id)
            .filter(
                TVMoviesCountry.country_id.in_(watched_countries),
                Movies.show_id != last_liked_show_id if last_liked_show_id else True,
            )
            .distinct()
            .limit(limit)
        )

        # Query for similar country TV shows
        similar_country_tvshows_query = (
            session.query(
                TVShow.show_id.label("show_id"),
                TVShow.title,
                TVShow.season.label("runtime"),
                TVShow.rating,
                TVShow.release_year,
                TVShow.description,
                TVShow.image,
            )
            .join(TVMoviesCountry, TVShow.show_id == TVMoviesCountry.show_id)
            .filter(
                TVMoviesCountry.country_id.in_(watched_countries),
                TVShow.show_id != last_liked_show_id if last_liked_show_id else True,
            )
            .distinct()
            .limit(limit)
        )

        # Execute the queries and combine results
        similar_country_movies_results = similar_country_movies_query.all()
        similar_country_tvshows_results = similar_country_tvshows_query.all()

        # Combine similar country movies and TV shows into a list of dictionaries
        similar_country_movies = []
        for row in similar_country_movies_results:
            similar_country_movies.append(
                {
                    "show_id": row.show_id,
                    "title": row.title,
                    "runtime": row.runtime,
                    "rating": row.rating,
                    "release_year": row.release_year,
                    "description": row.description,
                    "image_url": row.image,
                }
            )

        for row in similar_country_tvshows_results:
            similar_country_movies.append(
                {
                    "show_id": row.show_id,
                    "title": row.title,
                    "runtime": row.runtime,
                    "rating": row.rating,
                    "release_year": row.release_year,
                    "description": row.description,
                    "image_url": row.image,
                }
            )

        # Fetch the name of the liked genre
        liked_genre_name = (
            session.query(Genre.name).filter(Genre.id == liked_genre_id).scalar()
            if liked_genre_id
            else None
        )

        # Query for most liked movies across all users
        most_liked_movies_query = (
            session.query(
                Movies.show_id.label("show_id"),
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                func.count(WatchHistory.show_id).label("like_count"),
                Movies.image,
            )
            .join(WatchHistory, WatchHistory.show_id == Movies.show_id)
            .filter(WatchHistory.like_dislike == 1)
            .group_by(
                Movies.show_id,
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                Movies.image,
            )
            .order_by(desc(func.count(WatchHistory.show_id)))
            .limit(limit)
            .all()
        )

        # Query for most liked TV shows across all users
        most_liked_tvshows_query = (
            session.query(
                TVShow.show_id.label("show_id"),
                TVShow.title,
                TVShow.season.label("runtime"),
                TVShow.rating,
                TVShow.release_year,
                TVShow.description,
                func.count(WatchHistory.show_id).label("like_count"),
                TVShow.image,
            )
            .join(WatchHistory, WatchHistory.show_id == TVShow.show_id)
            .filter(WatchHistory.like_dislike == 1)
            .group_by(
                TVShow.show_id,
                TVShow.title,
                TVShow.season,
                TVShow.rating,
                TVShow.release_year,
                TVShow.description,
                TVShow.image,
            )
            .order_by(desc(func.count(WatchHistory.show_id)))
            .limit(limit)
            .all()
        )

        # Combine most liked movies and TV shows into a single list
        most_liked_shows = []
        for movie in most_liked_movies_query:
            most_liked_shows.append(
                {
                    "show_id": movie.show_id,
                    "title": movie.title,
                    "runtime": movie.runtime,
                    "rating": movie.rating,
                    "release_year": movie.release_year,
                    "description": movie.description,
                    "like_count": movie.like_count,
                    "image_url": movie.image,
                    "type": "Movie",
                }
            )

        for tvshow in most_liked_tvshows_query:
            most_liked_shows.append(
                {
                    "show_id": tvshow.show_id,
                    "title": tvshow.title,
                    "runtime": tvshow.runtime,
                    "rating": tvshow.rating,
                    "release_year": tvshow.release_year,
                    "description": tvshow.description,
                    "like_count": tvshow.like_count,
                    "image_url": tvshow.image,
                    "type": "TV Show",
                }
            )
        # Fetch 10 random movies for weekly highlights
        random_movies_query = (
            session.query(
                Movies.show_id.label("show_id"),
                Movies.title,
                Movies.runtime,
                Movies.rating,
                Movies.release_year,
                Movies.description,
                Movies.image,
            )
            .order_by(func.random())
            .limit(10)
            .all()
        )

        # Fetch 10 random TV shows for binge-watching
        random_tvshows_query = (
            session.query(
                TVShow.show_id.label("show_id"),
                TVShow.title,
                TVShow.season.label("runtime"),
                TVShow.rating,
                TVShow.release_year,
                TVShow.description,
                TVShow.image,
            )
            .order_by(func.random())
            .limit(10)
            .all()
        )

        # Combine random movies and TV shows into separate lists of dictionaries
        random_movies = []
        for row in random_movies_query:
            random_movies.append(
                {
                    "show_id": row.show_id,
                    "title": row.title,
                    "runtime": row.runtime,
                    "rating": row.rating,
                    "release_year": row.release_year,
                    "description": row.description,
                    "image_url": row.image,
                }
            )

        random_tvshows = []
        for row in random_tvshows_query:
            random_tvshows.append(
                {
                    "show_id": row.show_id,
                    "title": row.title,
                    "runtime": row.runtime,
                    "rating": row.rating,
                    "release_year": row.release_year,
                    "description": row.description,
                    "image_url": row.image,
                }
            )

        # get rating detail of hero movie
        watch_history = (
            session.query(WatchHistory)
            .filter_by(username=username, show_id=herosmovie[0]["show_id"])
            .first()
        )

        # Close the session
        session.close()
        print("CHEEBAI HURRY UP APPEAR HERE:", user.profile_pic)
        return render_template(
            "home.html",
            username=username,
            similar_genre_movies=similar_genre_movies,
            most_liked_shows=most_liked_shows,
            similar_country_movies=similar_country_movies,
            liked_genre_name=liked_genre_name,
            random_movies=random_movies,
            random_tvshows=random_tvshows,
            has_liked_content=has_liked_content,
            herosmovie=random_movies,
            watch_history=watch_history,
            user=user,
        )

    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()
        session.close()
        return "An error occurred while processing your request.", 500

@app.route("/discussion/<username>")
def show_discussion_form(username):
    return render_template('discussion-create.html', username=username)

@app.route('/user-forum/<username>')
def my_discussion(username):
    posts = posts_collection.find({"author_id": username})
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    
    if user.profile_pic:
        user.profile_pic = '/' + user.profile_pic  # Decode profile_pic from bytes to string
    session.close()
    return render_template('user-forums.html', user=user,username=username, posts=posts)
    

@app.route('/create-discussion/<username>', methods=['POST'])
def create_discussion(username):
    topic = request.form.get('topic')
    content = request.form.get('content')
    
    print(f"Topic: {topic}, Content: {content}")
    
    # Prepare the post document
    post = {
        "_id": ObjectId(),
        "topic_name": topic,
        "content": content,
        "author_id": username,
        "created_at": datetime.utcnow(),
        "replies": []
    }
    
    # Insert the document and capture the result
    result = posts_collection.insert_one(post)
    
    # Extract the post _id
    post_id = str(result.inserted_id)
    
    # # Redirect to the forum details page with username and post_id
    # return jsonify({
    #         "message": "Discussion created successfully!",
    #         "post_id": post_id
    #     })
    flash("Discussion created successfully!", "success")
    return redirect(url_for('forumdetails', username=username, id=post_id))
    
@app.route("/forum/<username>")
def forum(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if user.profile_pic:
        user.profile_pic = '/' + user.profile_pic  # Decode profile_pic from bytes to string
    session.close()
    
   
    posts = posts_collection.find({})
    
    return render_template("forum.html", user=user, username=username, posts=posts)

# Can use this when the db is set up 
# @app.route("/forum-details/<int:thread_id>")
# def forum_details(thread_id):
#     session = Session()
#     thread = session.query(ForumThread).filter_by(id=thread_id).first()
#     comments = session.query(ForumComment).filter_by(thread_id=thread_id).all()
#     session.close()
    
#     return render_template("forum-details.html", thread=thread, comments=comments)

def serialize_data(data):
    """ Recursively convert all ObjectId fields to strings in a dictionary """
    if isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_data(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    return data

@app.route("/forum-details/<username>/<id>")
def forumdetails(username, id):
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if user.profile_pic:
        user.profile_pic = '/' + user.profile_pic  # Decode profile_pic from bytes to string
    session.close()
    print("User:", user.username)
    post = posts_collection.find_one({"_id": ObjectId(id)})
    replies = list(replies_collection.find({"post_id": ObjectId(id)}))
    
    # Convert ObjectId fields to strings
    post = serialize_data(post)
    replies = serialize_data(replies)
    
    # Create a map of replies
    replies_map = {}
    for reply in replies:
        parent_id = reply.get('parent_reply_id')
        if parent_id:
            if parent_id not in replies_map:
                replies_map[parent_id] = []
            replies_map[parent_id].append(reply)
    
    # Include parent replies from the post
    if 'replies' in post:
        for parent_reply in post['replies']:
            parent_id = parent_reply.get('_id')
            if parent_id not in replies_map:
                replies_map[parent_id] = []  # Ensure the parent reply has an entry in the map
            # Add the parent reply to the map (not mixed with other replies)
            if 'root' not in replies_map:
                replies_map['root'] = []
            replies_map['root'].append(parent_reply)
    
    #for debugging
    #print("Post:", post)
    #print("Replies:", replies)
    
    # Serialize `replies_map` and `post` to ensure they are JSON-compatible
    serialized_replies_map = serialize_data(replies_map)
    #print("serialized_replies_map:", serialized_replies_map)
    
    return render_template("forum-details.html", user=user, username=username, post=post, replies_map=serialized_replies_map)

@app.route("/submit-comment", methods=["POST"])
def submit_comment():
    data = request.form.to_dict()
    post_id = data.get('post_id')
    parent_reply_id = data.get('parent_reply_id')
    content = data.get('content')
    author_id = data.get('author_id')
    
    # for debugging cuz ofc its not working
    print("Post ID:", post_id)
    print("Parent Reply ID:", parent_reply_id)
    print("Content:", content)
    print("Author_id:", author_id)
    

    if not post_id or not content or not author_id:
        return jsonify({'success': False, 'message': 'Invalid data'})

    new_comment = {
        '_id': ObjectId(),  # Generate a new ObjectId for the comment
        'author_id': author_id,
        'content': content,
        'created_at': datetime.utcnow()
    }

    if not parent_reply_id:
        # This is a direct comment on the post
        result = posts_collection.update_one(
            {'_id': ObjectId(post_id)},
            {'$push': {'replies': new_comment}}
        )
    else:
        # This is a reply to another comment
        new_comment['post_id'] = ObjectId(post_id)
        new_comment['parent_reply_id'] = ObjectId(parent_reply_id)
        replies_collection.insert_one(new_comment)

    return jsonify({'success': True})

""" @app.route("/user-forums/<username>")
def userforums(username):
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    
    posts = [
        {
            'id': 123,
            'title': 'Topic Name',
            'content': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua...',
            'author': 'Author Name'
        },
        # Add more posts as needed
    ]
    return render_template("user-forums.html", user=user, posts=posts) """

@app.route('/edit-post/<username>/<post_id>')
def edit_post(username, post_id):
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    post = posts_collection.find_one({"_id": ObjectId(post_id)})
    return render_template('edit-post.html', post=post, user=user)

@app.route('/update-post/<username>/<post_id>', methods=['POST'])
def update_post(username, post_id):
    topic_name = request.form.get('topic_name')
    content = request.form.get('content')

    update = posts_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"topic_name": topic_name, "content": content}}
    )
    return redirect(url_for('my_discussion', username=username))

if __name__ == '__main__':
    print("Executing SQL script at startup...")
    execute_sql_script()
    print("Starting Flask application...")
    app.run(debug=True)
