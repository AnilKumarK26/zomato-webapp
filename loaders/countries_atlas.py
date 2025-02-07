import pandas as pd
from pymongo import MongoClient

# Initialize client variable outside try block so it's available in finally
client = None

try:
    # MongoDB Atlas connection string with correct cluster URL
    connection_string = "mongodb+srv://anilkumarkedarsetty:rH7MSd7meS7jpYn3@zomato.wt5v2.mongodb.net/?retryWrites=true&w=majority&appName=zomato"
    
    # Connect to MongoDB Atlas
    client = MongoClient(connection_string)
    
    # Test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB Atlas")
    
    # This will create the database if it doesn't exist
    db = client['zomato_db']
    countries_collection = db['countries']

    # Read the Excel file
    country_code_path = 'C:\\Users\\anilk\\Downloads\\archive (12)\\Country-Code.xlsx'
    country_code_df = pd.read_excel(country_code_path, sheet_name='Sheet1')
    print("Successfully read Excel file")
    
    # Convert DataFrame to list of dictionaries
    country_data = country_code_df.to_dict('records')
    
    # Drop existing collection if it exists
    countries_collection.drop()

    # Insert the data
    result = countries_collection.insert_many(country_data)
    print(f"Successfully inserted {len(result.inserted_ids)} country records")
    
    # Create index
    countries_collection.create_index("Country Code", unique=True)
    print("Created index on Country Code")
    
    # Verify the upload by printing first few records
    print("\nFirst few records in the database:")
    for doc in countries_collection.find().limit(3):
        print(doc)

except FileNotFoundError:
    print(f"Error: Could not find the file at {country_code_path}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
    print("Full error:", e.__class__.__name__)
finally:
    if client:
        client.close()