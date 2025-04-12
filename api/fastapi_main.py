"""
FastAPI program to allow modular front-end
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastapi_models import FloorPriceResult, ProfileOrderOptimzerResult
from required_types import OrderType, ProfileOrder
from wfmarkettool import WFMarketTool

logging.basicConfig(
    filename="fastapi_main.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(funcName)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global wftool
    wftool = WFMarketTool(logger)
    await wftool.initialize()
    yield
    # Shutdown
    if wftool:
        await wftool.close()  # clean up


app = FastAPI(lifespan=lifespan)
wftool: WFMarketTool | None = None


@app.get("/wfmarkettool/item_floor_prices/{item_name}")
async def get_floor_prices(item_name: str = "", order_count: int = 5) -> FloorPriceResult:
    """
    Get the floor prices of multiple items in warframe.market
    """
    ret = []
    if wftool:
        ret = await wftool.get_item_floor_prices(item_name, order_count)
    else:
        raise Exception("WFtool not initialized")
    return ret


@app.get("/wfmarkettool/profile/{username}/sell")
async def get_profile_orders(username: str = "") -> list[ProfileOrder]:
    if wftool is None:
        raise Exception("WFtool not initialized")

    return await wftool.get_profile_orders(username, OrderType.SELL)


@app.get("/wfmarkettool/profile/{username}/optimize")
async def verify_profile_orders_optimality(
    username: str,
    order_type: OrderType = OrderType.SELL,
    floor_price_order_count: int = 5,
    visible_only: bool = True,
) -> list[ProfileOrderOptimzerResult]:
    if wftool is None:
        raise Exception("WFtool not initialized")

    return await wftool.verify_profile_orders_prices(
        username, order_type, floor_price_order_count, visible_only
    )
