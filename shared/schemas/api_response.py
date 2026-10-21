
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, model_validator, model_serializer

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

    @model_serializer(mode='wrap')
    def serialize_results(self, handler):
        from shared.presentation.result import normalize_results
        return normalize_results(handler(self))

    @model_validator(mode='after')
    def validate_data_and_error(self) -> 'APIResponse':
        if self.error is not None and self.data is not None:
            raise ValueError("Response cannot have both 'data' and 'error' simultaneously non-null.")
        return self
