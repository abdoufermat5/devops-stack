from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., pattern=r"^[a-z\-]+$")
    quantity: int = Field(default=1, ge=1)


class ProductUpdate(BaseModel):
    quantity: int | None = Field(None, ge=0)
    bought: bool | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    quantity: int
    bought: bool

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    id: int
    product_name: str
    quantity: int
    timestamp: str

    class Config:
        from_attributes = True
