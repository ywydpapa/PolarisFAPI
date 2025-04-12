from urllib import request
import uvicorn
from fastapi import FastAPI, Depends, Request, Form, Response, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
import dotenv
from datetime import datetime
import os
import pyupbit
import random


app = FastAPI()
dotenv.load_dotenv()
DATABASE_URL = os.getenv("dburl")
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/thumbnails", StaticFiles(directory="static/img/coincharts/"), name="thumbnails")
THUMBNAIL_DIR = "./static/img/coincharts"

async def get_db():
    async with async_session() as session:
        yield session


async def set_skey(userno: int, skey:str, db: AsyncSession):
    try:
        rightnow =datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = text("UPDATE polarisUser set sKey = :skey, lastLogin = :logtm where userNo = :userno")
        result = await db.execute(query, {"userno": userno, "skey": skey, "logtm": rightnow})
        await db.commit()
        return result
    except:
        raise HTTPException(status_code=500, detail="Database query failed(SetKey Process)")


async def check_session(userno: int, skey: str,db: AsyncSession):
    try:
        rightnow =datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = text("SELECT lastLogin FROM polarisUser WHERE userNo = :userno AND sKey = :skey")
        result = await db.execute(query, {"userno": userno, "skey": skey})
        if result.first() is None:
            error_message = " 세션이 만료되어 로그인이 필요합니다. 다시 시도해 주세요."
            return templates.TemplateResponse("login/login.html", {"request": request, "error": error_message})
        else:
            return {"userno": userno, "scheck": "POSITIVE"}
    except:
        raise HTTPException(status_code=500, detail="Database query failed(CheckSession Process)")


async def checkwallet(userno: int,db: AsyncSession):
    try:
        walletitems = []
        query = text("SELECT apiKey1, apiKey2 FROM polarisKeys WHERE userNo=:uno AND attrib NOT LIKE :att")
        mykeys = await db.execute(query, {"uno": userno, "att": '%XXX'})  # setkey 제거
        keys = mykeys.fetchone()
        if not keys:
            print("No available Keys !!")
        else:
            key1 = keys[0]
            key2 = keys[1]
            upbit = pyupbit.Upbit(key1, key2)
            walletitems = upbit.get_balances()
        return walletitems
    except Exception as e:
        print(f"Wallet Check Error: {e}")
        return []

def format_currency(value):
    if isinstance(value, (int, float)):
        return "₩{:,.0f}".format(value)
    return value

templates.env.filters['currency'] = format_currency

@app.get("/", response_class=HTMLResponse)
async def login_form(request: Request):
    if request.session.get("user_sKey"):
        return RedirectResponse(url="/logincheck", status_code=303)
    return templates.TemplateResponse("login/login.html", {"request": request})


@app.api_route("/login",response_class=HTMLResponse ,methods=["GET","POST"])
async def login(request: Request,userid: str = Form(...),password: str = Form(...), db: AsyncSession = Depends(get_db)):
    query = text("SELECT userNo, userName, userRole FROM polarisUser WHERE userId = :userid AND userPassword = password(:password)")
    result = await db.execute(query, {"userid": userid, "password": password})
    user = result.fetchone()
    if user is None:
        return templates.TemplateResponse("login/login.html", {"request": request, "error": "아이디와 암호가 틀립니다. 로그인 정보를 확인하고 다시 접속해 주세요"})
    setkey = random.randint(100000000, 999999999)
    await set_skey(user[0], setkey, db)
    request.session["user_No"] = user[0]
    request.session["user_Name"] = user[1]
    request.session["user_Role"] = user[2]
    request.session["user_sKey"] = setkey
    return RedirectResponse(url="/logincheck", status_code=303)

@app.get("/logincheck", response_class=HTMLResponse)
async def success_page(request: Request):
    user_No = request.session.get("user_No")
    user_Name = request.session.get("user_Name")
    user_Role = request.session.get("user_Role")
    user_sKey = request.session.get("user_sKey")
    if user_sKey:
        return templates.TemplateResponse("member/dashboardmain.html", {"request": request, "user_No": user_No, "user_Name": user_Name,"user_Role": user_Role, "user_sKey": user_sKey})
    else:
        error_message = " 세션이 만료되어 다시 로그인이 필요합니다."
        return templates.TemplateResponse("login/login.html", {"request": request, "error": error_message})

@app.get("/mywallet/{userno}", response_class=HTMLResponse)
async def mywallet(request:Request, userno: int, db: AsyncSession = Depends(get_db)):
    walletcont = await checkwallet(userno,db)
    return templates.TemplateResponse("member/mywallet.html", {"request": request, "user_No": userno, "witems": walletcont})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "/error/errorInfo.html",  # 템플릿 파일
            {"request": request, "error_message": "페이지를 찾을 수 없습니다."},  # 템플릿에 전달할 데이터
            status_code=404,
        )
    if exc.status_code == 500:
        return templates.TemplateResponse(
            "/error/errorInfo.html",  # 템플릿 파일
            {"request": request, "error_message": "시스템 내부 에러 발생."},  # 템플릿에 전달할 데이터
            status_code=500,
        )
    return HTMLResponse(
        content=f"<h1>{exc.status_code} - {exc.detail}</h1>",
        status_code=exc.status_code,
    )
