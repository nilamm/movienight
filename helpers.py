from flask import redirect, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def get_image_url(image_path, size='w500'):
    """Turns the image path into a full url"""

    if image_path:
        return ('https://image.tmdb.org/t/p/{size}{image_path}'
                .format(size=size, image_path=image_path))
    return 'http://www.reelviews.net/resources/img/default_poster.jpg'


def year_from_release_date(release_date):
    """Returns the year from the release date"""

    # Assumes format YYYY-MM-DD or YYYY
    return release_date.split("-")[0] if release_date else None


def genres_to_string(genres):
    """
    Returns a comma separated string of genres
    from the API's response.
    """
    if genres:
        return ", ".join([g["name"] for g in genres])
    return None
