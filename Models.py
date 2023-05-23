from pydantic import BaseModel
class Device(BaseModel):
     id : str
     os : str

class Time(BaseModel):
     a : float
     b : float

class File(BaseModel):
     file_hash : str
     file_path : str
     time : Time

class LastAccess(BaseModel):
     hash : str
     path : str
     pid : int

class Event(BaseModel):
    device : Device
    file : File
    last_access : LastAccess

class VerdictFile(BaseModel):
     hash : str
     risk_level : int

class Process(BaseModel):
     hash : str
     risk_level : int

class Verdict(BaseModel):
     file : VerdictFile
     process : Process

class HashVerdict(BaseModel):
     hash : str
