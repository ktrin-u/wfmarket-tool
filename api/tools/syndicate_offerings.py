"""
Program to acquire standing store items of syndicates
"""

import asyncio
import logging
import re
from collections.abc import Coroutine
from enum import StrEnum
from typing import Any

import aiohttp
from bs4 import BeautifulSoup


class SyndicateLinks(StrEnum):
    MERIDIAN = "https://warframe.fandom.com/wiki/Steel_Meridian"
    VEIL = "https://warframe.fandom.com/wiki/Red_Veil"
    HEXIS = "https://warframe.fandom.com/wiki/Arbiters_of_Hexis"
    SUDA = "https://warframe.fandom.com/wiki/Cephalon_Suda"
    PERRIN = "https://warframe.fandom.com/wiki/The_Perrin_Sequence"
    LOKA = "https://warframe.fandom.com/wiki/New_Loka"


class SyndicateOfferingScraper:
    """
    A class that scrapes Syndicate offerings
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._logger: logging.Logger | None = None

    async def initialize(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def _acquire_syndicate_page(self, syndicate: SyndicateLinks) -> str:
        if self._session is None:
            raise Exception("session has not be initialized")

        async with self._session.get(url=syndicate.value) as resp:
            match resp.status:
                case 200:
                    return await resp.text()
                case _:
                    raise Exception("expected http status 200, got {resp.status}")

    async def get_syndicate_offerings(self, syndicate: SyndicateLinks) -> list[str]:
        syndicate_html = BeautifulSoup(await self._acquire_syndicate_page(syndicate), "html.parser")

        offerings = syndicate_html.find_all(
            "span",
            attrs={"style": "color:black; font-weight:700; text-transform:uppercase;"},
        )
        offerings_text: list[str] = []

        for offering in offerings:
            text = re.sub(r"\(.*\)", "", offering.string)  # remove unicode representations
            text = text.strip(" \n").replace(" ", "_").lower()
            text = text.replace("'", "")
            offerings_text.append(text)

        def filter_offerings(offering: str) -> bool:
            untradeable = [
                "sigil",
                "specter",
                "emote",
                "set",
                "cache",
                "scene",
                "blueprint",
                "pack",
                "stencil",
                "simulacrum",
                "syandana",
                "sculpture",
            ]
            return all(word not in offering for word in untradeable)

        return list(filter(filter_offerings, offerings_text))  # type: ignore

    async def get_multiple_syndicate_offerings(self, syndicates: list[SyndicateLinks]) -> list[str]:
        awaitables: list[Coroutine[Any, Any, list[str]]] = list()
        ret: list[str] = list()

        for syndicate in syndicates:
            awaitables.append(self.get_syndicate_offerings(syndicate))

        results = await asyncio.gather(*awaitables)

        for result in results:
            ret += result
        return ret
