import os
import time
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import numpy as np
from pydantic import BaseModel
import socket
import uvicorn
from urllib.parse import urlencode
import pymongo
import datetime
import redis
from model import load_model
import random
from bluetooth_hr import HeartRateMonitor


model = load_model()
app = FastAPI(title="Health Monitor", version="1.0.0")
templates = Jinja2Templates(directory="templates")
db = pymongo.MongoClient("mongodb://localhost:27017/")["Health"]["HeartRate"]
re = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", "6379"),
    decode_responses=True,
)

# Initialize Bluetooth Heart Rate Monitor
hr_monitor = HeartRateMonitor(db_client=db)

means = [140.852179, 2.574585, 88.527766, 3221.042023]
stds = [15.532219, 0.448150, 3.825462, 2631.164519]

st = time.time()

@app.on_event("startup")
async def startup_event():
    """Start the Bluetooth heart rate monitor when the app starts."""
    print("Starting Bluetooth Heart Rate Monitor...")
    asyncio.create_task(hr_monitor.start())

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Bluetooth heart rate monitor when the app shuts down."""
    print("Stopping Bluetooth Heart Rate Monitor...")
    hr_monitor.stop()

@app.get("/api", include_in_schema=False)
async def index():
    """
    This endpoint redirects the root URL to the API documentation page.

    Returns:

        RedirectResponse: A redirection to the API documentation page.
    """
    return RedirectResponse(url="/docs")


class HeartRateData(BaseModel):
    bpm: int


@app.post("/", tags=["Heart Rate"])
async def post_hr(request: Request):
    """
    This endpoint receives a POST request with the heart rate data.

    Args:
        data (HeartRateData): The heart rate data.

    Returns:
        dict: A dictionary with the message "OK".
    """
    post_data = await request.body()
    bpm = int(post_data.decode("utf-8").split("=")[1])
    bpm = max(80, bpm)
    db.insert_one({"bpm": bpm, "timestamp": datetime.datetime.now()})
    return {"message": "OK"}


@app.get("/hr", tags=["Heart Rate"])
async def get_hr(hour: float = 0.05):
    """
    This endpoint returns the heart rate data from the last hour.

    Args:
        hour (int): The number of hours to retrieve the data from.

    Returns:
        dict: A dictionary with the heart rate data.
    """
    data = db.find(
        {"timestamp": {"$gt": datetime.datetime.now() - datetime.timedelta(hours=hour)}}
    )
    data = list(data)
    data = sorted(data, key=lambda x: x["timestamp"])                           

    for i in range(len(data)):
        del data[i]["_id"]
    bpm = [x["bpm"] for x in data]
    
    
    if len(bpm) < 60:
        re.set("hr", "0")
        return data
    
    # get the last 60 bpm values
    bpm = bpm[-60:]
    speed = [2.5] * len(bpm)
    cadence = [90] * len(bpm)
    distance = [(time.time() - st) * 2.5] * len(bpm)

    input = np.array([bpm, speed, cadence, distance])
    input = input.T   
    input = input.reshape(1, 60, 4)
    
    input = (input - means) / stds

    prediction = model.predict(input, verbose=False)
    # Denormalize the prediction
    prediction = prediction * stds[0] + means[0]

    pred = prediction[0][0] + random.randint(0, 3)
    re.set("hr", str(pred))


    return data

@app.get("/hr/next", tags=["Heart Rate"])
async def get_next_hr():
    """
    This endpoint returns the next heart rate prediction.

    Returns:
        dict: A dictionary with the next heart rate prediction.
    """
    # Check if hr is already in redis
    if re.get("hr") is None:
        return {"bpm": 0}
    pred = re.get("hr")
    return {"bpm": pred}

@app.get("/chart", tags=["Heart Rate"], response_class=HTMLResponse)
async def chart(request: Request):
    """
    This endpoint returns the chart page.

    Returns:
        TemplateResponse: The chart page.
    """
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    port_arg = 6547
    uvicorn.run("api:app", host="0.0.0.0", port=port_arg, reload=True)
