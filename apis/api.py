from urllib import request
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
import json
from datetime import datetime
import os
import pyupbit
import random


async def set_skey(userno: int, skey:str, db: AsyncSession):
    try:
        rightnow =datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = text("UPDATE polarisUser set sKey = :skey, lastLogin = :logtm where userNo = :userno")
        result = await db.execute(query, {"userno": userno, "skey": skey, "logtm": rightnow})
        await db.commit()
        return result
    except:
        raise HTTPException(status_code=500, detail="Database query failed(SetKey Process)")


async def get_key(userno:int, skey:str, db: AsyncSession):
    try:
        query = text("SELECT apiKey1, apiKey2 FROM polarisKeys WHERE userNo=:uno AND attrib NOT LIKE :att")
        mykeys = await db.execute(query, {"uno": userno, "att": '%XXX'})  # setkey 제거
        keys = mykeys.fetchone()
        if not keys:
            print("No available Keys !!")
        else:
            key1 = keys[0]
            key2 = keys[1]
        return key1, key2
    except:
        raise HTTPException(status_code=500, detail="Database query failed(GetKey Process)")


async def checkwallet(userno: int,db: AsyncSession):
    try:
        walletitems = []
        mycoins = []
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
            for wallet in walletitems:
                if wallet['currency'] != "KRW":
                    ccoin = "KRW-" + wallet['currency']
                    try:
                        cpr = pyupbit.get_current_price(ccoin)
                    except Exception as e:
                        cpr = 1
                    curr = [wallet['currency'], cpr]
                    mycoins.append(curr)
        return walletitems, mycoins
    except Exception as e:
        print(f"Wallet Check Error: {e}")
        return []


async def app_checkwallet(userno: int,db: AsyncSession):
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
            for wallet in walletitems:
                if wallet['currency'] != "KRW":
                    ccoin = "KRW-" + wallet['currency']
                    try:
                        cpr = pyupbit.get_current_price(ccoin)
                    except Exception as e:
                        cpr = 1
                    wallet['curprice'] = cpr
                else:
                    wallet['curprice'] = 1
        return json.dumps(walletitems)
    except Exception as e:
        print(f"Wallet Check Error: {e}")
        return []


def get_tick_size(price):
    if price >= 2000000:
        return 1000
    elif price >= 1000000:
        return 500
    elif price >= 500000:
        return 100
    elif price >= 100000:
        return 50
    elif price >= 10000:
        return 10
    elif price >= 1000:
        return 1
    elif price >= 100:
        return 0.1
    elif price >= 10:
        return 0.01
    elif price >= 1:
        return 0.001
    else:
        return 0.0001


def get_tick_size2(price):
    if price >= 2000000:
        return 1000
    elif price >= 1000000:
        return 500
    elif price >= 500000:
        return 100
    elif price >= 100000:
        return 50
    elif price >= 10000:
        return 10
    elif price >= 1000:
        return 1
    elif price >= 100:
        return 1
    elif price >= 10:
        return 0.01
    elif price >= 1:
        return 0.001
    else:
        return 0.0001


async def clearcache(db: AsyncSession):
    try:
        query = text("RESET QUERY CACHE")
        result = await db.execute(query)
        return result
    except:
        raise HTTPException(status_code=500, detail="Database query failed(ClearCache)")




