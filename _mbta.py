import os
from twython import Twython, TwythonStreamer
import requests
import json

# Setting Configuration settings
FORMAT = 'json' # response format for MBTA api
MBTA_API_KEY = os.environ.get('MBTA_API_KEY') # MBTA api key

def query_mbta(route_id):

    query_type = 'predictionsbyroute'

    # Build url to query the MBTA api
    url = 'http://realtime.mbta.com/developer/api/v2/%s?api_key=%s&route=%s&format=%s' % query_type, MBTA_API_KEY, route_id, FORMAT

    raw_response = requests.get(url).text
    decoded_json = json.loads(raw_response)

    # Navigate json object to find vehicle lat & lon
    vehicle = decoded_json['direction'][0]['trip'][0]['vehicle']
    lat = vehicle['vehicle_lat']
    lon = vehicle['vehicle_lon']

    return lat, lon

class MyStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            print data['text'].encode('utf-8')

    def on_error(self, status_code, data):
        print status_code

        # Want to stop trying to get data because of the error?
        # Uncomment the next line!
        # self.disconnect()

def main():
    # Twitter settings
    twitter = Twython(os.environ.get('TWITTER_KEY'),
                      os.environ.get('TWITTER_SECRET'),
                      os.environ.get('TWITTER_ACCESS_TOKEN'),
                      os.environ.get('TWITTER_ACCESS_STOKEN'))

    stream = MyStreamer(os.environ.get('TWITTER_KEY'),
                      os.environ.get('TWITTER_SECRET'),
                      os.environ.get('TWITTER_ACCESS_TOKEN'),
                      os.environ.get('TWITTER_ACCESS_STOKEN'))

    stream.statuses.filter(track='twitter')

    # query mbta api
    lat, lon = query_mbta('CR-Kingston')

if __name__ == '__main__':
    main()