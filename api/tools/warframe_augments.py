"""
Program to acquire warframe augment mods
"""

import json
import logging
import logging.config
from pathlib import Path
from typing import TypedDict

import aiohttp
from bs4 import BeautifulSoup, Tag


class WarframeAugments(TypedDict):
    augments: list[str]
    syndicates: tuple[str, str]


class WarframeAugmentsScraper:
    """
    A class that
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._ENDPOINT: str = "https://warframe.fandom.com/wiki/Warframe_Augment_Mods"

        if logger is None:
            config = {}
            with open(Path("cfg/logger.json", "r")) as cfg:
                config = json.load(cfg)
                config["handlers"]["file"]["filename"] = f"{__name__}.log"

            logging.config.dictConfig(config)
            self._logger = logging.getLogger(__name__)
        else:
            self._logger: logging.Logger = logger

    async def initialize(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def _acquire_augments_page(self) -> str:
        if self._session is None:
            raise Exception("session has not be initialized")

        async with self._session.get(url=self._ENDPOINT) as resp:
            match resp.status:
                case 200:
                    return await resp.text()
                case _:
                    raise Exception("expected http status 200, got {resp.status}")

    async def get_warframe_augments(self) -> dict[str, WarframeAugments]:
        augment_html = BeautifulSoup(await self._acquire_augments_page(), "html.parser")

        augment_table = augment_html.find(class_="wikitable")
        assert isinstance(augment_table, Tag)

        augment_tbody = augment_table.find("tbody")
        assert isinstance(augment_tbody, Tag)

        augment_table_rows = augment_tbody.find_all("tr")[1:]  # remove header row
        augments_list: dict[str, WarframeAugments] = {}

        for row in augment_table_rows:
            # pprint(row.find_all("span"))
            details: list[str] = list()
            for span in row.find_all("span", class_=""):
                details.append(span.string.replace("\xa0", "_").lower())

            warframe_name = details.pop(0)
            syndicates = (details.pop(-1), details.pop(-1))

            augments_list[warframe_name] = WarframeAugments(augments=details, syndicates=syndicates)

        return augments_list


async def main():
    scraper = WarframeAugmentsScraper()
    await scraper.initialize()

    print(await scraper.get_warframe_augments())

    await scraper.close()
