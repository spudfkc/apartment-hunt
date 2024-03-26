#!/usr/bin/env python3

import re
import os
import json
import asyncio
from scrapfly import ScrapflyClient, ScrapeConfig, ScrapeApiResponse
from bs4 import BeautifulSoup
from loguru import logger
from discord.ext import tasks
import discord
from dotenv import load_dotenv


class MyClient(discord.Client):
    floorplans = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}')

    async def my_background_task(self):
        await self.wait_until_ready()
        await asyncio.sleep(5)
        logger.info(f'starting background task w channel {os.environ["DISCORD_CHANNEL_ID"]}')
        counter = 0
        channel = await self.fetch_channel(os.environ["DISCORD_CHANNEL_ID"])
        logger.info(f'channel: {channel}')
        while not self.is_closed():
            counter += 1
            logger.info(f'sending: {counter}')
            for plan in self.floorplans:
                await channel.send(f"{plan}")
            # await channel.send(f"{self.floorplans}")
            await asyncio.sleep(60 * 60 * 4)  # task runs every 4 hrs


class Floorplan:
    beds = None
    baths = None
    price = None
    link = None
    title = None
    availability = None
    size = None

    def __str__(self):
        return f'Title: {self.title} - {self.beds} bed {self.baths} bath - {self.size} sq ft - ${self.price} - {self.availability} - {self.link}'

    def __repr__(self):
        return self.__str__()

    def is_available(self):
        return self.price != None and self.availability != 'Waitlist Available'


class AptParser:
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, 'html.parser')

    def parse_plans(self):

        parsed_plans = []

        plans = self.soup.find(id='fp-floor-plan-groups').find_all('div', class_='inner-card-container')

        for p in plans:
            floorplan = Floorplan()
            plan_data = json.loads(p.find('a', class_="primary").attrs['data-eptracking'])
            floorplan.beds = float(plan_data['bedroom'])
            floorplan.baths = float(plan_data['bathroom'])
            price = p.find('span', class_='small-text')
            try:
                price_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
                matches = re.findall(price_pattern, price.contents.pop().strip())
                floorplan.price = int(matches[0].replace('$', '').replace(',', ''))
            except Exception as e:
                logger.debug(f'no price found {e}')
            try:
                floorplan.link = f'https:{p.find("a", class_="primary").attrs["href"]}'
            except:
                logger.debug('no link found')
            try:
                floorplan.title = p.find('h2', class_='fp-title').contents.pop().strip()
            except:
                logger.debug('no title found')
            try:
                floorplan.availability = p.find('span', class_='availability').contents.pop().strip()
            except:
                logger.debug('no availability found')
            try:
                floorplan.size = int(p.find('span', class_='dynamic-text-after').contents.pop().strip().strip(' sq. ft').replace(',', ''))
            except:
                logger.debug('no size found')
            parsed_plans.append(floorplan)

        return parsed_plans


class DataLoader:
    def __init__(self):
        pass

    def load(self):
        ctn = None
        try:
            with open( 'site.cached', 'r') as f:
                ctn = f.read()
        except FileNotFoundError:
            scrapfly_key = os.environ['SCRAPFLY_API_KEY']
            url = os.environ['URL']
            scrapfly = ScrapflyClient(key=scrapfly_key)
            result: ScrapeApiResponse = scrapfly.scrape(ScrapeConfig(
                tags=[
                    "player","project:default"
                ],
                asp=True,
                render_js=True,
                url=url,
            ))
            ctn = result.content
            self.save(ctn)

        return ctn

    def save(self, ctn):
        with open('site.cached', 'w') as f:
            f.write(ctn)

load_dotenv()
bool_str = lambda x: x.lower() in ['true', '1', 't', 'y', 'yes']
discord_enabled = bool_str(os.environ.get("DISCORD_ENABLED"))

intents = discord.Intents.default()
client = MyClient(intents=intents)

loader = DataLoader()
ctn = loader.load()

parser = AptParser(ctn)
plans = parser.parse_plans()
logger.debug(f'found {len(plans)} total plans')

available_plans = list(filter(lambda x: x.is_available(), plans))
logger.debug(f'found {len(available_plans)} available plans: {available_plans}')
in_price_range_plans = list(filter(lambda x: x.price < int(os.environ['MAX_PRICE']), available_plans))
logger.debug(f'found {len(in_price_range_plans)} price acceptable plans: {in_price_range_plans}')

if discord_enabled:
    logger.info('Discord enabled')
    client.floorplans = in_price_range_plans
    client.run(os.environ['DISCORD_TOKEN'])

