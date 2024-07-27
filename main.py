import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = MongoClient(mongo_url)
db = client.taskdb
tasks_collection = db.tasks
users_collection = db.users

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Task(BaseModel):
    title: str
    description: str
    status: str


class User(BaseModel):
    username: str
    password: str


def get_current_user(token: str = Depends(oauth2_scheme)):
    user = users_collection.find_one({"token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Task Management System API"}


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"username": form_data.username})
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    return {"access_token": user["token"], "token_type": "bearer"}


@app.post("/tasks/")
async def create_task(task: Task, current_user: dict = Depends(get_current_user)):
    task_id = tasks_collection.insert_one(task.model_dump()).inserted_id
    return {"task_id": str(task_id)}


@app.get("/tasks/", response_model=List[Task])
async def get_tasks(current_user: dict = Depends(get_current_user)):
    tasks = list(tasks_collection.find())
    return tasks


@app.put("/tasks/{task_id}")
async def update_task(task_id: str, task: Task, current_user: dict = Depends(get_current_user)):
    tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": task.model_dump()})
    return {"message": "Task updated successfully"}


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    tasks_collection.delete_one({"_id": ObjectId(task_id)})
    return {"message": "Task deleted successfully"}


@app.get("/debug")
async def debug():
    users = list(users_collection.find())
    tasks = list(tasks_collection.find())
    for user in users:
        user["_id"] = str(user["_id"])
    for task in tasks:
        task["_id"] = str(task["_id"])
    return {"users": users, "tasks": tasks}
