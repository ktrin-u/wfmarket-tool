"""
Collection of Types and Protocols to ensure static typing
"""

from enum import StrEnum, auto
from typing import Required, TypedDict, TypeVar

T = TypeVar("T")
Platinum = int  # type alias for clarity


class Status(StrEnum):
    """
    An enum that contains all the possible values for the Warframe Market status
    """

    INGAME = auto()
    ONLINE = auto()
    OFFLINE = auto()


class OrderType(StrEnum):
    """
    An enum that contains all possible values for the Warframe Market order type
    """

    BUY = auto()
    SELL = auto()


# class APIOptions(StrEnum):
#     """
#     An enum that contains the path of the actions supported by the warframe.market api
#     """
#     GET_TRADEABLE_ITEMS = "/items"
#     GET_ITEM = "/items"


class WFToolOperations(StrEnum):
    """
    An enum that contains the path of the actions supported by the wfmarkettool
    """

    ITEM_ORDERS = auto()
    PROFILE_ORDERS = auto()


class User(TypedDict):
    """
    A class that defines the contents of the User object for the Warframe Market response
    """

    reputation: int
    locale: str
    avatar: str
    ingame_name: str
    last_seen: str
    id: str
    region: str
    status: Status


class ItemNameLocalization(TypedDict, total=False):
    item_name: str


class Item(TypedDict, total=False):
    thumb: str
    icon: str
    url_name: Required[str]
    id: Required[str]
    vaulted: bool
    icon_format: str
    sub_icon: str | None
    subtypes: list[str]
    mod_max_rank: int
    tags: list[str]
    en: ItemNameLocalization
    ru: ItemNameLocalization
    ko: ItemNameLocalization
    fr: ItemNameLocalization
    sv: ItemNameLocalization
    de: ItemNameLocalization
    zh_hant: ItemNameLocalization
    zh_hans: ItemNameLocalization
    pt: ItemNameLocalization
    es: ItemNameLocalization
    pl: ItemNameLocalization
    cs: ItemNameLocalization
    uk: ItemNameLocalization
    it: ItemNameLocalization


class Order(TypedDict, total=False):
    creation_date: str
    visible: bool
    quantity: int
    platinum: Required[Platinum]
    last_update: str
    region: str
    id: Required[str]
    order_type: OrderType
    mod_rank: int
    subtype: str


class ItemOrder(Order, total=False):
    """
    A class that defines the contents of the Order object for the Warframe Market response
    """

    user: Required[User]


class ProfileOrder(Order, total=False):
    item: Required[Item]


class Payload(TypedDict, total=False):
    """
    A class that defines the contents of the payload object for the Warframe Market response
    """

    orders: list[ItemOrder]  # result from GET request to API_endpoint/items/{item_name}/orders
    sell_orders: list[
        ProfileOrder
    ]  # result from GET request to API_endpoint/profile/{username}/orders
    buy_orders: list[
        ProfileOrder
    ]  # result from GET request to API_endpoint/profile/{username}/orders


class WFMarketResponse(TypedDict, total=False):
    """
    A class that defines the contents of the Warframe Market response
    """

    payload: Payload
