# app.py
import os
from werkzeug.utils import secure_filename
from math import ceil
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from pymongo import MongoClient, GEOSPHERE
from bson import ObjectId
import tensorflow as tf
import numpy as np
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
connection_string = f"mongodb+srv://{os.getenv('MONGODB_USERNAME')}:{os.getenv('MONGODB_PASSWORD')}@{os.getenv('MONGODB_CLUSTER')}.wt5v2.mongodb.net/?retryWrites=true&w=majority&appName={os.getenv('MONGODB_DATABASE')}"
client = MongoClient(connection_string)
db = client[os.getenv('MONGODB_DATABASE')]
restaurant_collection = db['restaurants']
countries_collection = db['countries']
restaurants_json_collection = db['restaurants_json']  # Add this line

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FOOD_TO_CUISINE_MAPPING = {
    'pizza': ['Italian', 'American'],
    'hamburger': ['American', 'Fast Food'],
    'ice cream': ['Desserts', 'Ice Cream'],
    'pasta': ['Italian', 'Continental'],
    'sushi': ['Japanese', 'Asian'],
    'curry': ['Indian', 'Thai', 'Asian'],
    'noodles': ['Chinese', 'Asian', 'Thai'],
    'sandwich': ['American', 'Fast Food'],
    'cake': ['Desserts', 'Bakery'],
    'salad': ['Healthy Food', 'Continental']
}

def get_restaurant_image(restaurant_name):
    """Fetch restaurant image from restaurants_json collection"""
    restaurant_data = restaurants_json_collection.find_one(
        {'name': restaurant_name},
        {'featured_image': 1}
    )
    return restaurant_data.get('featured_image') if restaurant_data else '/static/default-restaurant.jpg'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_image_classification_model():
    return tf.keras.applications.MobileNetV2(weights='imagenet')

def process_image(image_path):
    model = load_image_classification_model()
    
    img = tf.keras.preprocessing.image.load_img(
        image_path, 
        target_size=(224, 224)
    )
    img_array = tf.keras.preprocessing.image.img_to_array(img)
    img_array = tf.expand_dims(img_array, 0)
    img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
    
    predictions = model.predict(img_array)
    decoded_predictions = tf.keras.applications.mobilenet_v2.decode_predictions(predictions)
    
    food_items = []
    for pred in decoded_predictions[0]:
        class_name = pred[1].lower().replace('_', ' ')
        confidence = float(pred[2])
        
        for food_key in FOOD_TO_CUISINE_MAPPING.keys():
            if food_key in class_name:
                food_items.append({
                    'name': food_key,
                    'confidence': confidence,
                    'cuisines': FOOD_TO_CUISINE_MAPPING[food_key]
                })
                break
    
    return food_items

def generate_pagination_range(current_page, total_pages, window=2):
    pages = set([1, total_pages])
    
    for i in range(max(1, current_page - window), min(total_pages + 1, current_page + window + 1)):
        pages.add(i)
    
    page_list = sorted(list(pages))
    final_range = []
    
    for i, page in enumerate(page_list):
        if i > 0:
            if page - page_list[i-1] > 1:
                final_range.append('...')
        final_range.append(page)
    
    return final_range

@app.route('/')
def index():
    try:
        page = int(request.args.get('page', 1))
        per_page = 9
        
        country = request.args.get('country')
        price_range = request.args.get('price_range')
        search_query = request.args.get('search')
        cuisines = request.args.getlist('cuisines')
        
        filters = {}
        if country:
            filters['Country Code'] = int(country)
        if search_query:
            filters['$text'] = {'$search': search_query}
        if cuisines:
            filters['Cuisines'] = {'$in': cuisines}

        total_count = restaurant_collection.count_documents(filters)
        total_pages = ceil(total_count / per_page)
        
        page = max(1, min(page, total_pages))
        
        restaurants = list(restaurant_collection.find(
            filters
        ).skip((page - 1) * per_page).limit(per_page))
        
        # Add featured image to each restaurant
        for restaurant in restaurants:
            restaurant['_id'] = str(restaurant['_id'])
            restaurant['featured_image'] = get_restaurant_image(restaurant['Restaurant Name'])
        
        pagination_range = generate_pagination_range(page, total_pages)
        countries = list(countries_collection.find({}, {'_id': 0}))
        
        return render_template(
            'index.html',
            restaurants=restaurants,
            countries=countries,
            current_page=page,
            total_pages=total_pages,
            pagination_range=pagination_range,
            unique_cuisines = restaurant_collection.distinct('Cuisines')
        )
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('index'))

@app.route('/restaurant/<restaurant_id>')
def restaurant_detail(restaurant_id):
    try:
        restaurant = restaurant_collection.find_one({'_id': ObjectId(restaurant_id)})
        if restaurant:
            restaurant['_id'] = str(restaurant['_id'])
            # Add featured image
            restaurant['featured_image'] = get_restaurant_image(restaurant['Restaurant Name'])
            return render_template('restaurant_detail.html', 
                                 restaurant=restaurant,
                                 google_maps_api_key=os.getenv('GOOGLE_MAPS_API_KEY'))
        flash('Restaurant not found')
        return redirect(url_for('index'))
    except Exception as e:
        flash('Invalid restaurant ID')
        return redirect(url_for('index'))

@app.route('/search')
def search():
    try:
        query = request.args.get('q', '')
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        
        filters = {}
        if query:
            filters['$text'] = {'$search': query}
        
        if lat and lon:
            lat, lon = float(lat), float(lon)
            
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                flash('Invalid latitude or longitude')
                return redirect(url_for('search'))
            
            filters['location'] = {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [lon, lat]
                    },
                    '$maxDistance': 3000  
                }
            }
        
        restaurants = list(restaurant_collection.find(filters).limit(20))
        
        # Add featured image to each restaurant
        for restaurant in restaurants:
            restaurant['_id'] = str(restaurant['_id'])
            restaurant['featured_image'] = get_restaurant_image(restaurant['Restaurant Name'])
        
        return render_template('search.html', restaurants=restaurants, query=query, lat=lat, lon=lon)
    except ValueError:
        flash('Latitude and Longitude must be numeric')
        return redirect(url_for('search'))
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('search'))

@app.route('/image-search', methods=['GET', 'POST'])
def image_search():
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No image file provided')
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                food_items = process_image(filepath)
                
                cuisines = []
                for food_item in food_items:
                    cuisines.extend(food_item['cuisines'])
                
                cuisines = list(set(cuisines))
                
                restaurants = list(restaurant_collection.find({
                    'Cuisines': {'$in': cuisines}
                }).limit(12))
                
                # Add featured image to each restaurant
                for restaurant in restaurants:
                    restaurant['_id'] = str(restaurant['_id'])
                    restaurant['featured_image'] = get_restaurant_image(restaurant['Restaurant Name'])
                
                os.remove(filepath)
                
                return render_template('image_search.html', 
                                     results={'detected_foods': food_items,
                                             'restaurants': restaurants})
            
            except Exception as e:
                flash(f'Error processing image: {str(e)}')
                return redirect(request.url)
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
    
    return render_template('image_search.html')

if __name__ == '__main__':
    try:
        client.admin.command('ping')
        print("Successfully connected to MongoDB Atlas")
        
        restaurant_collection.create_index([('location', GEOSPHERE)])
        print("Created geospatial index")
        
        restaurant_collection.create_index([("Restaurant Name", "text")])
        print("Created text search index")
        
        app.run(debug=True)
    except Exception as e:
        print(f"Error during startup: {str(e)}")
