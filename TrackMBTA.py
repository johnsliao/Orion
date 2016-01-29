# Built-in imports
import os
import requests
import json
import time
import logging

# Third-party dependencies
from twython import Twython, TwythonStreamer
from create_image import create_image
from config import twitter, MBTA_API_KEY

# Global init
FORMAT = 'json' # response format for MBTA api

# Commuter rail lines
ROUTES = {"CR-Fairmount":"Fairmount Line",
          "CR-Fitchburg":"Fitchburg Line",
          "CR-Worcester":"Framingham/Worcester Line",
          "CR-Franklin":"Franklin Line",
          "CR-Greenbush":"Greenbush Line",
          "CR-Haverhill":"Haverhill Line",
          "CR-Lowell":"Lowell Line",
          "CR-Needham":"Needham Line",
          "CR-Newburyport":"Newburyport/Rockport Line",
          "CR-Providence":"Providence/Stoughton Line",
          "CR-Kingston":"Kingston/Plymouth Line",
          "CR-Middleborough":"Middleborough/Lakeville Line",
          }

DIRECTIONS = ['inbound', 'outbound']
BACKOFF = 0.5 # Retry time to twitter API
MAX_BACKOFF = 300 # Max retry time before exiting

logging.basicConfig(filename='logger.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

BLACKLIST = ['trackmbta'] # must be lower case

def query_mbta(route_id, direction_name):

    query_type = 'predictionsbyroute'

    # Build url to query the MBTA api
    base_url = 'http://realtime.mbta.com/developer/api/v2/'
    url = '%s%s?api_key=%s&route=%s&format=%s' % (
        base_url,
        query_type,
        MBTA_API_KEY,
        route_id,
        FORMAT)

    logging.info("Generated MBTA api query url, %s" % url)

    raw_response = requests.get(url).text
    decoded_json = json.loads(raw_response)

    if 'error' in decoded_json:
        logging.info("MBTA api query error for route_id: %s" % route_id)
        raise ValueError('MBTA api query error. Route not found')

        return 0, 0, None

    directions = [direction for direction in decoded_json['direction']]

    for direction in directions:
        mbta_direction_name = direction['direction_name'].lower()
        mbta_trip_name = direction['trip'][0]['trip_name']
        mbta_trip_headsign = direction['trip'][0]['trip_headsign']
        mbta_vehicle = direction['trip'][0]['vehicle']
        mbta_trip_id = direction['trip'][0]['trip_id']

        lat = mbta_vehicle['vehicle_lat']
        lon = mbta_vehicle['vehicle_lon']

        if mbta_direction_name == direction_name:
            logging.info("Successfully retrieval for line %s, %s, %s, %s" % (mbta_trip_id,
                                                                             route_id,
                                                                             mbta_trip_name,
                                                                             mbta_trip_headsign,
                                                                             mbta_direction_name))
            return lat, lon, mbta_trip_name, mbta_trip_headsign, mbta_direction_name

    logging.info("MBTA api query successful, however could not find trip: %s, %s" % (route_id, direction_name))

    return 0, 0, None

def generate_reply_tweet(tweet_from, mbta_direction_name, trip_name, mbta_trip_headsign):
    return "@%s %s %s train location" % (tweet_from, mbta_trip_headsign, mbta_direction_name)

def generate_error_tweet(TrackMBTA, tweet_from, tweet_id):
    logging.info("Tweeting back now: @%s Sorry I couldn't find the train location!" % (tweet_from))
    TrackMBTA.update_status(status=("@%s Sorry I couldn't find the train location!" % (tweet_from)),
                            in_reply_to_status_id=tweet_id)

def does_route_exist(route_input):
    for route_id, route_name in ROUTES.items():
        if route_input in route_name.lower():
            return route_id

    return None

def does_direction_exit(direction_input):
    for direction in DIRECTIONS:
        if direction_input in direction:
            return direction

    return None

class MyStreamer(TwythonStreamer):
    def on_success(self, data):
        # Twitter settings
        TrackMBTA = Twython(twitter['key'],
                            twitter['secret_key'],
                            twitter['token'],
                            twitter['secret_token'])

        tweet_text = data['text'].lower()
        tweet_from = data['user']['screen_name']
        tweet_id = data['id']
        in_reply_to_status_id = data['in_reply_to_status_id']

        logging.info("TWITTER STREAM TWEET (containg @TrackMBTA): %s" % tweet_text)

        """
            Acceptable tweet format:

            @TrackMBTA <Train Line> <Direction>

        """

        if tweet_from not in BLACKLIST and in_reply_to_status_id is None:
            split_tweet = tweet_text.split(' ') # Not very robust way to parse tweet. Fix later


            my_handle = split_tweet[0] # @TrackMBTA
            route_input = split_tweet[1].lower() # <Train Line>
            direction_input = split_tweet[2].lower() # Direction

            route_id = does_route_exist(route_input)
            direction_name = does_direction_exit(direction_input)

            if route_id is not None:
                if direction_name is not None:
                    logging.info("Tweet received: %s from %s" % (tweet_text, tweet_from))

                    # Will return lat, lon = 0,0 if no train found
                    lat, lon, trip_name, mbta_trip_headsign, mbta_direction_name = query_mbta(route_id, direction_name)

                    if lat is not 0 and lon is not 0:
                        # Generate reply tweet
                        reply_tweet = generate_reply_tweet(tweet_from, mbta_direction_name, trip_name, mbta_trip_headsign)

                        # Generate google map
                        create_image(lat, lon)

                        # Respond with tweet
                        path_to_map = "./images/maps/%s,%s.jpg" % (lat,lon)

                        if os.path.exists(path_to_map) is True:
                            logging.info("Saving map file to %s" % path_to_map)
                            fname = open(path_to_map, 'rb')
                            logging.info("Generated reply tweet: %s" % reply_tweet)
                            TrackMBTA.update_status_with_media(status=reply_tweet,
                                                               media=fname,
                                                               in_reply_to_status_id=tweet_id)
                        else:
                            raise ImportError("Import file error, %s" % path_to_map)
                    else:
                        generate_error_tweet(TrackMBTA, tweet_from, tweet_id)
                else:
                    generate_error_tweet(TrackMBTA, tweet_from, tweet_id)
            else:
                generate_error_tweet(TrackMBTA, tweet_from, tweet_id)

    def on_error(self, status_code, data):
        global BACKOFF

        if status_code == 420:
            logging.info('420 error code, retry in %s seconds' % BACKOFF)
            time.sleep(BACKOFF)
            BACKOFF = BACKOFF * 2

            if BACKOFF > MAX_BACKOFF:
                logging.error("Max backoff exceeded")
                exit('max retry time exceeded')
        else:
            logging.info("Status code: %s" % status_code)

def main():
    stream = MyStreamer(twitter['key'],
                        twitter['secret_key'],
                        twitter['token'],
                        twitter['secret_token'])

    stream.statuses.filter(track='TrackMBTA')
    #print query_mbta('CR-Lowell', 'Iutbound')

if __name__ == '__main__':
    main()
