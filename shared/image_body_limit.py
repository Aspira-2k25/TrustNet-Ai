"""Bound image request bodies before multipart parsing or proxy buffering."""
import os
from fastapi import HTTPException
from starlette.responses import JSONResponse

class ImageBodyLimit:
    def __init__(self, app, paths, max_bytes=None):
        self.app=app;self.paths=set(paths)
        self.limit=(max_bytes or int(os.getenv('MAX_IMAGE_SIZE_MB','10'))*1024*1024)+65536

    async def __call__(self, scope, receive, send):
        if scope['type']!='http' or scope.get('path') not in self.paths:
            return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]))
        length=headers.get(b'content-length')
        try:
            declared=int(length) if length is not None else 0
            if declared<0:raise ValueError()
        except ValueError:
            return await JSONResponse({'error':{'code':'INVALID_CONTENT_LENGTH'}},status_code=400)(scope,receive,send)
        detail={'code':'FILE_TOO_LARGE','message':'Image request exceeds the bounded upload budget'}
        if declared>self.limit:
            return await JSONResponse({'data':None,'error':detail},status_code=413)(scope,receive,send)
        total=0
        async def bounded_receive():
            nonlocal total
            message=await receive()
            total+=len(message.get('body',b''))
            if total>self.limit:raise HTTPException(413,detail=detail)
            return message
        return await self.app(scope,bounded_receive,send)
