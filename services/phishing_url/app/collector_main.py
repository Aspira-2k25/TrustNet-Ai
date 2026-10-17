"""Optional collector process: deploy separately from internal service networks."""
import asyncio
import hmac
import multiprocessing
import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from services.phishing_url.app.services.metadata_collector import collect

app=FastAPI(title="Phishing isolated collector")
@app.get('/health')
def health():
    return {'status':'ok','token_configured':bool(os.getenv('PHISHING_COLLECTOR_TOKEN'))}

capacity=asyncio.Semaphore(4)
class Request(BaseModel):
    url:str=Field(min_length=4,max_length=2048)
    include_html:bool=False
def child(pipe,url,include_html):
    try: pipe.send(collect(url,include_html))
    except Exception as exc: pipe.send({"status":"unavailable","reason":type(exc).__name__})
    finally: pipe.close()

def bounded_collect(url,include_html):
    context=multiprocessing.get_context("spawn")
    parent,remote=context.Pipe(duplex=False)
    process=context.Process(target=child,args=(remote,url,include_html))
    process.start();remote.close()
    try:
        if not parent.poll(25): raise TimeoutError("Collector deadline exceeded")
        return parent.recv()
    finally:
        parent.close()
        if process.is_alive():process.terminate()
        process.join(timeout=2)

@app.post("/collect")
async def metadata(request:Request,x_collector_token:str=Header(default="")):
    token=os.getenv("PHISHING_COLLECTOR_TOKEN","")
    if not token or not hmac.compare_digest(token,x_collector_token):raise HTTPException(403,"Collector access denied")
    from models.phishing_url.preprocessing.url_parser import parse_url
    try:parse_url(request.url)
    except ValueError:raise HTTPException(422,"Invalid URL")
    async with capacity:
        try:return await asyncio.to_thread(bounded_collect,request.url,request.include_html)
        except TimeoutError:raise HTTPException(504,"Collection timed out")
