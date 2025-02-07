import pandas as pd
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['zomato_db']  
countries_collection = db['countries']  

# Read the Excel file
country_code_path = 'C:\\Users\\anilk\\Downloads\\archive (12)\\Country-Code.xlsx'
try:
    country_code_df = pd.read_excel(country_code_path, sheet_name='Sheet1')
    print("Successfully read Excel file")
    
    country_data = country_code_df.to_dict('records')
    
    countries_collection.drop()

    result = countries_collection.insert_many(country_data)
    print(f"Successfully inserted {len(result.inserted_ids)} country records")
    
    countries_collection.create_index("Country Code", unique=True)
    print("Created index on Country Code")
    

    print("\nFirst few records in the database:")
    for doc in countries_collection.find().limit(3):
        print(doc)

except FileNotFoundError:
    print(f"Error: Could not find the file at {country_code_path}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
finally:
    client.close()