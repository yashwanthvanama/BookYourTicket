from config import GOOGLE_MAPS_API_KEY
import googlemaps
import math

# Initialize the Google Maps client with your API key
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Create a function to get latitude and longitude for an address
def get_lat_long_for_address(address):
    geocode_result = gmaps.geocode(address)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        return None
    
def get_formatted_address_for_lat_long(lat, long):
    geocode_result = gmaps.reverse_geocode((lat, long))
    if geocode_result:
        return geocode_result[0]['formatted_address']
    else:
        return None

# Find the next few autocomplete results for a input string
def autocomplete_city(address):
    autocomplete_city_results = gmaps.places_autocomplete(address, types='(cities)')
    if autocomplete_city_results:
        return [result['description'] for result in autocomplete_city_results]
    else:
        return None
    
def get_distance(lat1, long1, lat2, long2):
    # Radius of the Earth in kilometers
    earth_radius = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(lat1)
    long1 = math.radians(long1)
    lat2 = math.radians(lat2)
    long2 = math.radians(long2)

    # Haversine formula
    dlon = long2 - long1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Calculate the distance
    distance = earth_radius * c

    return distance
