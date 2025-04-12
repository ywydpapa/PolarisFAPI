import dotenv
from fastapi import FastAPI
import dotenv
from datetime import datetime


app = FastAPI()
dotenv.load_dotenv()


def format_currency(value):
    if isinstance(value, (int, float)):
        return "₩{:,.0f}".format(value)
    return value

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
