from fastapi import FastAPI
import requests
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["weather_dashboard"]
collection = db["weather_data"]

@app.get("/")
def root():
    return {"message": "Weather API is running!"}

@app.get("/weather/{city}")
def get_weather(city: str):
    cached = collection.find_one({"city": city})
    if cached:
        return cached["data"]

    response = requests.get("https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.12&current_weather=true")
    data = response.json()
    collection.insert_one({"city": city, "data": data})
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)