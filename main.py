from fastapi import FastAPI, Depends, HTTPException, UploadFile
import uvicorn
import functools
import Models as models
import pymongo
import motor.motor_asyncio
import hashlib
import requests



app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Lab2"}

@app.get("/verdicts/{hash}/")
async def return_verdict(verdict : models.Verdict, hash : str):
     verdict.file.hash = hash
     verdict.process.hash = hash
     return verdict

@functools.lru_cache()
def mongo_data_collection():
    client = motor.motor_asyncio.AsyncIOMotorClient(
        "mongodb://root:example@localhost:27018"
    )
    db = client["data"]
    collection = db["verdicts"]
    return collection

# @mongo_router.post("/", response_model=SaveToMongoResponse)
async def save_to_mongo(data_in : models.HashVerdict, mongo_collection):
     await mongo_collection.insert_one(data_in.dict())


@app.post("/events/")
async def create_event(event : models.Event, mongo_collection=Depends(mongo_data_collection)):
     #    insert_one = await mongo_collection.insert_one({"hash" : event.file.file_hash})
        data = await mongo_collection.find_one({"hash" : event.file.file_hash})
        data2 = await mongo_collection.find_one({"hash" : event.last_access.hash})
        file_risk_level = -1
        process_risk_level = -1
        if data:
             file_risk_level = data["risk_level"]

        if data2:
             process_risk_level = data2["risk_level"]

        verdict_file = models.VerdictFile(hash=event.file.file_hash, risk_level=file_risk_level)
        verdict_process = models.Process(hash=event.last_access.hash, risk_level=process_risk_level)
        verdict = models.Verdict(file=verdict_file, process=verdict_process)
        return verdict

#to do
MOCK_DB = {}


@app.post("/scan_file/")
async def upload (file: UploadFile, mongo_collection=Depends(mongo_data_collection)) -> models.Verdict:
     file_content = await file.read()
     url = "https://beta.nimbus.bitdefender.net/liga-ac-labs-cloud/blackbox-scanner"
     try:
          black_box_api_res = requests.post(url, files={"file": ("file.txt", file_content)}).json()
     except Exception as e:
          raise HTTPException(status_code=400, detail=str(e))
     
     md5 = black_box_api_res['hash']
     risk_level = black_box_api_res['ris_level']
     verdict = models.Verdict()

@app.post("/scan_file/")
async def upload(file: UploadFile) -> models.Verdict:
    content = await file.read()

    # TODO trimis fișier la blackbox service și luat risk_level din răspuns
    md5 = hashlib.md5(content).hexdigest()
    risk_level = int(md5, 16) % 4

    # TODO: scris risk_level în mongo pentru a fi găsit ulterior de /events
    MOCK_DB[md5] = risk_level

    return models.Verdict(hash=md5, risk_level=risk_level)

# @app.post("/mongotest/")
# async def do_find_one():
#     client = motor.motor_asyncio.AsyncIOMotorClient('localhost', 27017)
#     db = client.test_database
#     collection = db.test_collection
#     document = await db.test_collection.find_one({'i': {'$lt': 1}})
#     print.print(document)

# @app.post("/insertToMongo/")
# async def do_insert_one():


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)