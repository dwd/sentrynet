from typing import Optional, Union
from pydantic import BaseModel


class Assertion(BaseModel):
    type: Optional[str] = None
    exists: bool = True
    value: Optional[Union[str,int,bool]] = None


class ProbeRequest(BaseModel):
    url: str
    method: Optional[str] = None
    body: Optional[dict] = None
    expected: int = 200
    set_keys: Optional[dict] = None
    assertions: Optional[dict[str,Assertion]] = None
