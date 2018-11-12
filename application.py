from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import urllib.parse

from helpers import login_required, get_image_url, \
    year_from_release_date, genres_to_string
import movieapi

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///movies.db")


@app.route("/")
@login_required
def index():
    """Show list of movies"""

    # For the template
    title = "My List"
    header_title = "My List"  # for page title in the header
    error = ("Welcome to Movie Night! Search for movies to add "
             "them to your list.")

    # Get all movies for this logged-in user
    movies = db.execute("""
        SELECT movies.*
        FROM movie_lists
        LEFT JOIN movies ON movies.id = movie_lists.movie_id
        WHERE user_id = :user
        """, user=session["user_id"])

    if len(movies) > 0:
        movie_posters = [get_image_url(m["poster_path"]) for m in movies]
        movie_years = [year_from_release_date(m["release_date"])
                       for m in movies]
        movie_results = list(zip(movies, movie_posters, movie_years))

    return render_template('list-movies.html',
                           movies=movie_results if len(movies) > 0 else None,
                           title=title, error=error,
                           header_title=header_title)


@app.route('/search', methods=["GET", "POST"])
@login_required
def search():
    """Search for movies"""

    # For template
    title = "Search Results"
    header_title = "Search Results"  # for page title in the header
    error = "Sorry, nothing matched your search."

    if request.method == "POST":
        url_query = urllib.parse.quote_plus(request.form.get("search"))
        return redirect('/search?q=' + url_query)

    if request.args.get("q"):
        movies = movieapi.search(request.args.get("q"))
    else:
        movies = []

    if len(movies) > 0:
        movie_posters = [get_image_url(m["poster_path"]) for m in movies]
        movie_years = [year_from_release_date(m["release_date"])
                       for m in movies]
        movie_results = list(zip(movies, movie_posters, movie_years))

    return render_template('list-movies.html',
                           movies=movie_results if len(movies) > 0 else None,
                           title=title, error=error,
                           header_title=header_title)


@app.route('/compare', methods=["GET", "POST"])
@login_required
def compare():
    if request.method == "POST":
        users_str = request.form.getlist("users")

        # TODO: What if no checkboxes were selected -- validate in html/jquery

        user_ids = [int(u) for u in users_str]
        user_ids.append(session["user_id"])
        all_movies = db.execute("""
            SELECT *
            FROM movie_lists
            WHERE user_id IN (:user_ids)
            """, user_ids=user_ids)

        movie_sets = []
        for user in user_ids:
            movie_sets.append(set([m["movie_id"] for m in all_movies
                                   if m["user_id"] == user]))

        common_movie_ids = set.intersection(*movie_sets)

        # Get data on the common movies
        movies = db.execute("""
            SELECT * FROM movies
            WHERE id IN (:movie_ids)
            """, movie_ids=list(common_movie_ids))

        if len(movies) > 0:
            movie_posters = [get_image_url(m["poster_path"]) for m in movies]
            movie_years = [year_from_release_date(m["release_date"])
                           for m in movies]
            movie_results = list(zip(movies, movie_posters, movie_years))

        # For template
        title = "Your Shared Movies"
        error = "Sorry, you don't have any movies in common."
        header_title = "Shared Movies"

        return render_template('list-movies.html',
                               movies=(movie_results if len(movies) > 0
                                       else None),
                               title=title, error=error,
                               header_title=header_title)

    # Get a list of other users
    users = db.execute("""
        SELECT * FROM users
        WHERE id <> :user_id
        """, user_id=session["user_id"])

    return render_template('compare.html', users=users)


@app.route('/movie/delete/<int:movie_id>', methods=["POST"])
@login_required
def delete_movie(movie_id):
    db.execute("""
        DELETE FROM movie_lists
        WHERE user_id = :user_id
        AND movie_id = :movie_id
        """, user_id=session["user_id"], movie_id=movie_id)

    return redirect("/movie/{}".format(movie_id))


@app.route('/movie/<int:movie_id>', methods=["GET", "POST"])
@login_required
def movie(movie_id):
    # Get data about this movie
    movie = movieapi.get_movie(movie_id)

    if request.method == "POST":
        # Insert user into db
        db.execute("""
            INSERT INTO movie_lists (user_id, movie_id)
            VALUES (:user_id, :movie_id)""",
                   user_id=session["user_id"],
                   movie_id=movie_id)

        # Insert movie into db if it's not already there
        if movie:
            db.execute("""
                INSERT OR IGNORE INTO movies
                (id, overview, poster_path, release_date,
                runtime, tagline, title)
                VALUES
                (:id, :overview, :poster_path, :release_date,
                :runtime, :tagline, :title)
                """, id=movie_id, overview=movie.get("overview"),
                       poster_path=movie.get("poster_path"),
                       release_date=movie.get("release_date"),
                       runtime=movie.get("runtime"),
                       tagline=movie.get("tagline"),
                       title=movie.get("title"))

        return redirect("/movie/{}".format(movie_id))

    # Check if movie is already on user's list
    res = db.execute("""
        SELECT count(*) as count_on_list FROM movie_lists
        WHERE user_id = :user_id
        AND movie_id = :movie_id
        """, user_id=session["user_id"], movie_id=movie_id)

    on_list = res[0]["count_on_list"] > 0

    print("MOVIE:\n\n", movie)

    return render_template('movie.html',
                           movie=movie,
                           poster=get_image_url(movie["poster_path"]),
                           on_list=on_list,
                           year=year_from_release_date(movie["release_date"]),
                           genres=genres_to_string(movie["genres"]))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        errors = []

        # Ensure username was submitted
        if not request.form.get("username"):
            errors.append("Missing username.")

        # Ensure password was submitted
        if not request.form.get("password"):
            errors.append("Misssing password.")

        # If either username or password is missing,
        # render errors on login page
        if not (request.form.get("username") and request.form.get("password")):
            return render_template("login.html", error=" ".join(errors))

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
                rows[0]["hash"], request.form.get("password")):
            return render_template("login.html",
                                   error="Incorrect username and/or password.")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        errors = []

        # Ensure username was submitted
        if not request.form.get("username"):
            errors.append("Missing username.")

        # Ensure password was submitted
        if not request.form.get("password"):
            errors.append("Missing password.")

        if not (request.form.get("username") and request.form.get("password")):
            return render_template("register.html", error=" ".join(errors))

        if not request.form.get("confirmation"):
            return render_template("register.html",
                                   error="Please confirm your password.")

        # Ensure confirmation matches password
        if not request.form.get("password") == \
                request.form.get("confirmation"):
            return render_template("register.html",
                                   error="Passwords don't match.")

        # Check if username is already taken
        user_resp = db.execute("""
            SELECT * FROM users
            WHERE username = :username""",
                               username=request.form.get("username"))

        if len(user_resp) > 0:
            return render_template("register.html",
                                   error=("Sorry, this username is "
                                          "already taken."))

        # Insert user into db
        db_resp = db.execute("""
            INSERT INTO users (username, hash)
            VALUES (:username, :hashed_pw)""",
                             username=request.form.get("username"),
                             hashed_pw=generate_password_hash(
                                request.form.get("password")))

        # Login
        session.clear()
        session["user_id"] = db_resp

        return redirect("/")
    return render_template("register.html")


# @app.errorhandler(HTTPException)
def errorhandler(error):
    """Handle errors"""
    print("\n\nERRORS", error)
    return render_template("error.html", error=error), error.code


# https://github.com/pallets/flask/pull/2314
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
