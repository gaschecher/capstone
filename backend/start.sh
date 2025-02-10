#!/bin/bash

# Function to test if MongoDB is ready
wait_for_mongodb() {
    echo "Waiting for MongoDB to be ready..."
    while ! python -c "from pymongo import MongoClient; MongoClient('$MONGO_URI')" 2>/dev/null; do
        sleep 1
    done
    echo "MongoDB is ready!"
}

# Wait for MongoDB
wait_for_mongodb

# Run data preprocessing with container paths
echo "Running data preprocessing..."
DATA_DIR=/app/data ZILLOW_DIR=/app/zillow-data python data_preprocessing.py

# Start the API
echo "Starting the API..."
python app.py
