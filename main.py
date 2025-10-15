from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import requests

load_dotenv()

app = FastAPI()

# List all frontend origins you use (include production + preview)
origins = [
    "https://weather-dashboard-frontend-bwj93bdrn-declanmerrys-projects.vercel.app",
    "https://weather-dashboard-frontend-tau.vercel.app",
    "http://localhost:5173",  # local dev
]

# Also allow any *.vercel.app (e.g. preview deploys)
@app.middleware("http")
async def add_dynamic_cors_header(request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin and origin.endswith(".vercel.app"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # only allow these
    allow_credentials=True,          # safe for cookies/auth
    allow_methods=["*"],             # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],             # allow all request headers
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
