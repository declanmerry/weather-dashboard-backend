from fastapi import FastAPI
import requests
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()

# Allow your frontend to access this API
app.add_middleware(
    CORSMiddleware,
    #allow_origins=[
    #    "https://weather-dashboard-frontend-bwj93bdrn-declanmerrys-projects.vercel.app",
    #    "https://weather-dashboard-frontend-tau.vercel.app"
    #],
    #allow_credentials=True,
    allow_origins=["*"],    
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["weather_dashboard"]
collection = db["weather_data"]

@app.get("/")
def root():
    return {"message": "Weather API is running!"}

@app.get("/weather/{city}")
def get_weather(city: str):
    city_normalized = city.strip().lower()  # normalize for caching

    # Check cache
    cached = collection.find_one({"city": city_normalized})
    if cached:
        return cached["data"]

    # Step 1: Get latitude/longitude using Open-Meteo geocoding
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_normalized}&count=1"
    geo_response = requests.get(geo_url)
    geo_data = geo_response.json()

    if "results" not in geo_data or not geo_data["results"]:
        return {"error": f"City '{city}' not found."}

    lat = geo_data["results"][0]["latitude"]
    lon = geo_data["results"][0]["longitude"]

    # Step 2: Fetch current weather for that location
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    weather_response = requests.get(weather_url)
    data = weather_response.json()

    # Step 3: Cache the result in MongoDB
    collection.insert_one({"city": city_normalized, "data": data})

    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
