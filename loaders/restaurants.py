from pymongo import MongoClient, GEOSPHERE
import pandas as pd

client = MongoClient('mongodb://localhost:27017/')
db = client['zomato_db']
collection = db['restaurants']
try:
    collection.drop()

    file_path = r'C:\Users\anilk\Downloads\archive (12)\zomato.csv'
    data = pd.read_csv(file_path, encoding='ISO-8859-1')
    boolean_columns = ['Has Table booking', 'Has Online delivery', 'Is delivering now', 'Switch to order menu']
    for col in boolean_columns:
        data[col] = data[col].map({'Yes': True, 'No': False})
    data['Cuisines'] = data['Cuisines'].str.split(',').apply(lambda x: [cuisine.strip() for cuisine in x] if isinstance(x, list) else [])

    data['location'] = data.apply(
        lambda row: {
            'type': 'Point',
            'coordinates': [float(row['Longitude']), float(row['Latitude'])]
        }, axis=1
    )
    data_dict = data.to_dict('records')

    result = collection.insert_many(data_dict)
    print(f"Inserted {len(result.inserted_ids)} documents into the collection.")
    
    # Create indexes
    collection.create_index([("location", GEOSPHERE)])
    collection.create_index([("Restaurant Name", "text")])
    collection.create_index("Country Code")
    collection.create_index("Cuisines")
    collection.create_index("Price range")
    print("Created indexes for: geospatial queries, text search, country code, cuisines, and price range")
    
    # Verify some data
    print("\nFirst document in collection:")
    print(collection.find_one())

except FileNotFoundError:
    print(f"Error: Could not find the file at {file_path}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
finally:
    client.close()