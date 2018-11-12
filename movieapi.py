import requests
import os

base_url = 'https://api.themoviedb.org/3/'
_key = os.getenv('MOVIE_DB_AUTH')


def request_endpoint(endpoint, payload):
    """GET request an endpoint"""
    r = requests.get(base_url + endpoint, params=payload)
    if r.status_code == 200:
        return r.json()
    return None


def search(q, n_results=12):
    """Use the API's search functionality to query movies"""
    endpoint = 'search/movie'
    payload = {
        'page': 1,
        'include_adult': False,
        'language': 'en-US',
        'query': q,
        'api_key': _key
    }

    res = request_endpoint(endpoint, payload)
    if res.get("results"):
        return res["results"][:n_results]
    return []


def get_movie(movie_id):
    """Get a single movie by ID from the API"""
    endpoint = 'movie/{}'.format(movie_id)
    payload = {
        'language': 'en-US',
        'api_key': _key
    }
    return request_endpoint(endpoint, payload)
