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
    "https://weather-dashboard-frontend-m6iudr1ey-declanmerrys-projects.vercel.app",
    "https://weather-dashboard-frontend-kfnvsp0z4-declanmerrys-projects.vercel.app",
    "https://weather-dashboard-frontend-q4t6669i1-declanmerrys-projects.vercel.app",
    "https://weather-dashboard-frontend-10f36hb2e-declanmerrys-projects.vercel.app",
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

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["weather_dashboard"]
collection = db["weather_data"]

# --- API Keys ---
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

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

    # 2️⃣ Fetch from Open-Meteo
    open_meteo_url = "https://api.open-meteo.com/v1/forecast"
    open_meteo_params = {"latitude": 51.5, "longitude": -0.12, "current_weather": True}
    meteo_response = requests.get(open_meteo_url, params=open_meteo_params)
    meteo_data = meteo_response.json()

    # 3️⃣ Fetch from OpenWeatherMap
    openweather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={OPENWEATHER_API_KEY}"
    openweather_response = requests.get(openweather_url)
    openweather_data = openweather_response.json()

    # 4️⃣ Combine results
    combined = {
        "city": city.title(),
        "open_meteo": meteo_data.get("current_weather", {}),
        "open_weather": {
            "temp": openweather_data.get("main", {}).get("temp"),
            "feels_like": openweather_data.get("main", {}).get("feels_like"),
            "weather": openweather_data.get("weather", [{}])[0].get("description"),
            "wind_speed": openweather_data.get("wind", {}).get("speed"),
        },
    }

    # 5️⃣ Cache in MongoDB
    collection.insert_one({"city": city.lower(), "data": combined})

    return combined

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
