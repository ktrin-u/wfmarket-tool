"""
The class that contains all the functions for the main feature
"""

import asyncio
import json
import logging
import logging.config
import pprint
from collections.abc import Sequence
from pathlib import Path

import aiohttp

from fastapi_models import FloorPriceResult, ProfileOrderOptimzerResult
from required_types import (
    ItemOrder,
    Order,
    OrderType,
    Payload,
    Platinum,
    ProfileOrder,
    Status,
    WFMarketResponse,
    WFToolOperations,
)


class WFMarketTool:
    """
    Class for the WF Market Tool, designed for async
    Made to simplify querying the prices of multiple items

    Attributes:
        ENDPOINT (constant): the warframe.market api endpoint
        REQUEST_LIMIT (constant): wfmarket ToS states a max of 3 requests per second
        _request_counter (int): keeps track of number of requests made during the current second
        _session (aiohttp.ClientSession): an aiohttp ClientSession for web access
        _lock (asyncio.Lock): a synchronization primitive to ensure that the request counter is reset correctly
        _logger (Logger): a reference to the logger
        _request_timer (Task): a reference to the timer task

    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """
        Initializes a WFMarketTool object

        Parameters:
            logger (logging.Logger): the logger object to be used
        """

        self._ENDPOINT = "https://api.warframe.market/v1"
        self._REQUEST_LIMIT: int = 3
        self._request_counter: int = 0
        self._session: aiohttp.ClientSession | None = None
        self._lock: asyncio.Lock | None = None
        self._request_timer: asyncio.Task[None] | None = None
        self._item_db: Path

        if logger is None:
            config = {}
            with open(Path("cfg/logger.json", "r")) as cfg:
                config = json.load(cfg)
                config["handlers"]["file"]["filename"] = f"{__name__}.log"

            logging.config.dictConfig(config)
            self._logger = logging.getLogger(__name__)
        else:
            self._logger: logging.Logger = logger

    @property
    def ENDPOINT(self):
        return self._ENDPOINT

    @property
    def REQUEST_LIMIT(self) -> int:
        return self._REQUEST_LIMIT

    async def initialize(self) -> None:
        """
        For initializing async objects
        """
        self._session = aiohttp.ClientSession()
        self._lock = asyncio.Lock()
        self._request_timer = asyncio.create_task(self._request_timer_update())

    async def close(self) -> None:
        """
        Cleans up the session and request timer task
        """
        if self._session:
            await self._session.close()
        if self._request_timer:
            self._request_timer.cancel()

    async def _request_timer_update(self) -> None:
        """
        A periodic timer that refreshes itself every second to ensure compliance with ToS
        """
        while True:
            if not self._lock:
                raise Exception("lock object not initialized")

            async with self._lock:
                self.request_counter = 0
                self._logger.info("request counter refreshed")
            await asyncio.sleep(1)

    async def _check_request_time_valid(self) -> bool:
        """
        Ensures that the request is still within ToS limits
        """
        if not self._lock:
            raise Exception("lock object not initialized")

        async with (
            self._lock
        ):  # need to lock this part to ensure that request_counter is consistent
            if self.request_counter >= self.REQUEST_LIMIT:
                return False

            self.request_counter += 1
            self._logger.info("new request made")
            return True

    async def _process_name(self, item_name: str) -> str:
        """
        Removes trailing characters and replaces all spaces with underscores

        Parameters:
            item_name (str): the name of the item
        """
        return item_name.strip(" \n").replace(" ", "_")

    async def _get_payload(self, operation: WFToolOperations, target_name: str) -> Payload | None:
        """
        Sends a GET response to the API endpoint and attempts to acquire the
        payload value of the response

        Parameters:
            item_name (str): the name of the item

        Returns:
            WFMarketResponse: the response in the form of a dictionary to expect from a GET request
        """
        if self._session is None:
            raise Exception("aiohttp ClientSession not initialized")

        if not (await self._check_request_time_valid()):
            self._logger.info("request_limit reached, trying again in 1s")
            await asyncio.sleep(1)
            return await self._get_payload(operation, target_name)

        target_name = await self._process_name(target_name)  # attempt to generalize input parameter
        self._logger.info(f"attempting to acquire {operation.value} {target_name}")
        target_url: str = f"{self.ENDPOINT}"

        match operation:
            case WFToolOperations.ITEM_ORDERS:
                target_url += f"/items/{target_name.lower()}/orders"  # ensure lower case

            case WFToolOperations.PROFILE_ORDERS:
                target_url += f"/profile/{target_name}/orders"  # usernames are case-sensitive

            # case _:
            #     self._logger.error("unsupported operation found, raising exception")
            #     raise Exception("unsupported operation found")

        self._logger.info(f"target url: {target_url}")

        async with self._session.get(
            url=target_url,
        ) as result:
            match result.status:
                case 200:
                    self._logger.info(f"successfully acquired {operation.value} {target_name}")
                    response: WFMarketResponse = await result.json()
                    if response is not None:
                        return response.get("payload")
                case _:
                    self._logger.warning(f"expected http status 200, got http code {result.status}")

        self._logger.warning(f"failed to acquire {operation.value} {target_name}", RuntimeWarning)
        return {}

    async def _validate_item_name(self, item_name: str) -> bool: ...

    async def _filter_item_orders(
        self, orders: list[ItemOrder], key_order_type: OrderType = OrderType.SELL
    ) -> list[ItemOrder]:
        """
        Limit all orders to sell orders only

        Parameters:
            orders (list[Order]): a list of all the orders

        Returns:
            list[Orders]: a list of all the Orders for {item_name} limited to sell orders only
        """
        if type(orders) is not list:
            raise TypeError("argument is expected to be of type list")

        def remove_non_in_game(order: ItemOrder) -> bool:
            user = order.get("user")
            if user is not None:
                status = user.get("status")
                if status is not None:
                    match status:
                        case Status.INGAME.value:
                            return True
                        case Status.ONLINE.value:
                            return False
                        case Status.OFFLINE.value:
                            return False
                        case _:
                            logging.warning(
                                f"unsupported status type found in order id {order['id']}",
                                RuntimeWarning,
                            )
                            return False
            raise Exception(f"order {order['id']} has no user key")

        def filter_func(order: ItemOrder) -> bool:
            order_type = order.get("order_type")
            if order_type is None:
                logging.warning(f"order with id {order['id']} is invalid", RuntimeWarning)
                return False
            if order_type is not None and order_type == key_order_type.value:
                return remove_non_in_game(order)
            # logging.warning(f"unsupported order type \"{order_type}\" found")
            return False

        return list(filter(filter_func, orders))

    async def _get_plat_prices(
        self, orders: Sequence[Order], sort_descending: bool = False
    ) -> list[Platinum]:
        """
        Gets all the platinum prices from the a list of orders

        Parameters:
            sell_orders (list[Order]): a list of sell-orders
            sort_descending (bool): indicate whether the return value should sorted in descending order, defaults to False

        Returns:
            list[Platinum]: a list of containing all the prices of the orders
        """
        prices: list[Platinum] = []
        for order in orders:
            plat = order.get("platinum")
            if type(plat) is Platinum:
                prices.append(plat)
                continue
            self._logger.warning(f"order {order['id']} has no platinum key", RuntimeWarning)

        if sort_descending:
            prices.sort(reverse=True)
            return prices

        prices.sort()
        return prices

    async def get_item_orders(
        self, item_name: str, order_type: OrderType = OrderType.SELL
    ) -> list[ItemOrder]:
        """
        Get the order key of the payload

        Parameters:
            item_name (str): the name of the item

        Returns:
            list[Order]: a list of all the Orders for {item_name}
        """
        payload = await self._get_payload(WFToolOperations.ITEM_ORDERS, item_name)
        if payload is None:
            self._logger.warning("unable to get orders from payload None", RuntimeWarning)
            return list()

        orders: list[ItemOrder] | None = payload.get("orders")
        if orders is None:
            self._logger.warning(f"failed to acquire item orders of {item_name}", RuntimeWarning)
            return list()

        return await self._filter_item_orders(orders, order_type)

    async def get_item_floor_prices(self, item_name: str, order_count: int = 5) -> FloorPriceResult:
        """
        Gets the {order_count} lowest prices for {item_name}

        Parameters:
            item_name (str): the name of the item
            order_count (int): the number of floor prices to list

        Returns:
            FloorPriceResult: a Pydantic model that contains the item name and the bottom {order_count} prices
        """
        sell_orders = await self.get_item_orders(item_name, OrderType.SELL)
        plat_prices = await self._get_plat_prices(sell_orders)
        return FloorPriceResult(item_name=item_name, prices=plat_prices[:order_count])

    async def print_multiple_floor_prices(
        self, item_name_list: list[str], order_count: int = 5
    ) -> None:
        """
        Gets the {order_count} lowest prices for multiple items

        Parameters:
            item_name_list (list[str]): a list containing item_names
            order_count (int): the number of floor prices to list
        """
        awaitables: list[asyncio.Task[FloorPriceResult]] = []
        for item_name in item_name_list:
            task = asyncio.create_task(self.get_item_floor_prices(item_name, order_count))
            task.add_done_callback(
                lambda ret: pprint.pprint(f"{ret.result().item_name}: {ret.result().prices}")
            )
            awaitables.append(task)
            # awaitables.append(self.get_floor_prices(item_name, order_count))

        await asyncio.wait(awaitables)

    async def get_profile_orders(
        self, username: str, order_type: OrderType = OrderType.SELL
    ) -> list[ProfileOrder]:
        payload = await self._get_payload(WFToolOperations.PROFILE_ORDERS, username)
        if payload is None:
            self._logger.warning("unable to get orders from payload None", RuntimeWarning)
            return list()

        ret: list[ProfileOrder] | None = None
        match order_type:
            case OrderType.SELL:
                ret = payload.get("sell_orders")

            case OrderType.BUY:
                ret = payload.get("buy_orders")

        return ret if ret is not None else list()

    async def verify_profile_orders_prices(
        self,
        username: str,
        order_type: OrderType = OrderType.SELL,
        order_count: int = 5,
        visible_only: bool = True,
    ) -> list[ProfileOrderOptimzerResult]:
        """
        This function is used to determine if all listed visible {order_type} orders are within the {order_count} lowest prices
        to ensure sell time is fast

        Retrieves all the {order_type} orders of user {username}
        Then, it matches each order of the retrieved orders to its corresponding list of {order_count} lowest prices
        """
        # get all profile orders
        profile_orders = await self.get_profile_orders(username, order_type)

        # remove all non visible orders if specified
        if visible_only:
            self._logger.info("removing hidden orders")

            def filter_visibility(order: Order) -> bool:
                return bool(order.get("visible"))

            profile_orders = list(filter(filter_visibility, profile_orders))

        # get floor prices of each order
        ret: list[ProfileOrderOptimzerResult] = list()

        for profile_order in profile_orders:
            item_details = profile_order.get("item")
            if item_details is None:
                msg = "profile order with no item key encountered"
                self._logger.error(msg)
                raise Exception(msg)

            item_name = item_details.get("url_name")
            floor_price_result = await self.get_item_floor_prices(item_name, order_count)

            ret.append(
                ProfileOrderOptimzerResult(
                    item_name=item_name,
                    listed_price=profile_order.get("platinum"),
                    floor_prices=floor_price_result.prices,
                )
            )

        return ret
