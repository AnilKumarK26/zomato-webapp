import json
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['zomato_db']
restaurant_collection = db['restaurants_json']

# Load JSON file with UTF-8 encoding
with open('C:\\Users\\anilk\\Downloads\\totaldata.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# If data is nested, you might need to extract the restaurant data
processed_data = [item['restaurant'] for item in data]

# Insert data
restaurant_collection.insert_many(processed_data)

print(f"Inserted {len(processed_data)} restaurants")