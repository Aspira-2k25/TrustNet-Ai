
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, model_validator

DataT = TypeVar('DataT')

class ErrorDetail(BaseModel):
    code: str
    message: str

class ResponseMeta(BaseModel):
    request_id: str

class APIResponse(BaseModel, Generic[DataT]):
    data: Optional[DataT] = None
    error: Optional[ErrorDetail] = None
    meta: ResponseMeta

    @model_validator(mode='after')
    def validate_data_and_error(self) -> 'APIResponse':
        if self.error is not None and self.data is not None:
            raise ValueError("Response cannot have both 'data' and 'error' simultaneously non-null.")
        return self
