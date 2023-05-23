import functools
import hashlib

import motor.motor_asyncio
import requests
import uvicorn
from fastapi import FastAPI, UploadFile, Depends, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import redis
import os
import bson.json_util as json_util
import json
import aio_pika
from aio_pika import DeliveryMode, ExchangeType

app = FastAPI()
Instrumentator().instrument(app).expose(app)
redis_client = redis.Redis(host="redis", port=6379, db=0)
MONGO_URL = os.getenv('MONGO_URL') or "mongodb://root:example@localhost:27018"

class Time(BaseModel):
    a: int
    m: int


class Device(BaseModel):
    id: str
    os: str


class File(BaseModel):
    file_hash: str
    file_path: str
    time: Time


class Process(BaseModel):
    hash: str
    path: str
    pid: str


class Event(BaseModel):
    device: Device
    file: File
    last_access: Process


class Verdict(BaseModel):
    hash: str
    risk_level: int


class EventsResponse(BaseModel):
    file: Verdict
    process: Verdict

# def find_in_redis():


@functools.lru_cache()
def mongo_data_collection():
    # client = motor.motor_asyncio.AsyncIOMotorClient(
    #     "mongodb://root:example@mongo:27017"
    # )
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client["data"]
    collection = db["verdicts"]
    return collection

# def find_in_redis(file):
#     response = redis_client.get(file)
#     response_string = json.dumps(response)
#     return response_string

def find_in_redis(data):
    res = redis_client.get(data)
    res_string = json.dumps(res)
    if res is not None:
        return res_string
    else:
        return None


# @app.post("/events/")
# async def events(event: Event, mongo_collection=Depends(mongo_data_collection)) -> EventsResponse:
#     response = {}


#     for key, md5 in [('file', event.file.file_hash), ('process', event.last_access.hash)]:
#         redis_data = find_in_redis(md5)
#         if redis_data is None:
#             data = await mongo_collection.find_one({"hash": md5})
#             if data is not None:
#                 risk_level = data['risk_level']
#                 data_string = json.dumps(data)
#                 redis_client.set(md5, data_string)
#                 redis_client.expire(md5, 1000)
#             else:
#                 risk_level = -1
#                 redis_client.set(md5, -1)
#                 redis_client.expire(md5, 1000)

#         else:
#             risk_level = redis_data['risk_level']
#         response[key] = Verdict(hash=md5, risk_level=risk_level)

#     return EventsResponse(**response)

async def rabbitmq_exchange():
    # Perform connection
    connection = await aio_pika.connect("amqp://user:bitnami@rabbitmq/")
    # Creating a channel
    channel = await connection.channel()
    return await channel.declare_exchange(
        "logs", ExchangeType.FANOUT,
    )


logs_exchange = None


@app.post("/events/")
async def events(event: Event, mongo_collection=Depends(mongo_data_collection)) -> EventsResponse:
    response = {}
    global logs_exchange
    if logs_exchange is None:
        logs_exchange = await rabbitmq_exchange()

    message = aio_pika.Message(
        event.json().encode(),
        delivery_mode=DeliveryMode.PERSISTENT,
    )
    await logs_exchange.publish(message, routing_key="test")


    for key, md5 in [('file', event.file.file_hash), ('process', event.last_access.hash)]:
        redis_result = find_in_redis(md5)
        if redis_result is None:
            data = await mongo_collection.find_one({"hash": md5})
            if data is not None:
                redis_client.set(json_util.dumps(md5), json_util.dumps(data))
        else:
            data = redis_result

        if data is not None:
            risk_level = data['risk_level']
        else:
            risk_level = -1

        response[key] = Verdict(hash=md5, risk_level=risk_level)

    return EventsResponse(**response)



@app.post("/scan_file/")
async def upload(file: UploadFile, mongo_collection=Depends(mongo_data_collection)) -> Verdict:
    file_content = await file.read()

    url = "https://beta.nimbus.bitdefender.net/liga-ac-labs-cloud/blackbox-scanner/"
    try:
        black_box_api_response = requests.post(url, files={"file": ("file.txt", file_content)}).json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    md5 = black_box_api_response['hash']
    risk_level = black_box_api_response['risk_level']
    verdict = Verdict(hash=md5, risk_level=risk_level)
    await mongo_collection.insert_one(verdict.dict())
    print(f'Item created, {verdict=}')
    return verdict


if __name__ == "__main__":
    # uvicorn.run(app)
    uvicorn.run(app, port=8000, host="0.0.0.0")
