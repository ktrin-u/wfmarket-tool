"""
Collection of FastAPI models
"""

from pydantic import BaseModel

from .required_types import Platinum


class FloorPriceResult(BaseModel):
    item_name: str
    prices: list[Platinum]


class ProfileOrderOptimzerResult(BaseModel):
    item_name: str
    listed_price: Platinum
    floor_prices: list[Platinum]
