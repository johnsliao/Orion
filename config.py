import os

# Twitter settings
twitter = dict(key = os.environ.get('TWITTER_KEY'),
            secret_key = os.environ.get('TWITTER_SECRET'),
            token = os.environ.get('TWITTER_ACCESS_TOKEN'),
            secret_token = os.environ.get('TWITTER_ACCESS_STOKEN'))

# MBTA api settings
MBTA_API_KEY = os.environ.get('MBTA_API_KEY') # MBTA api key