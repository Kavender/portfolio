import os
import requests
import urllib.request as urllib2
from lxml import html
from bs4 import BeautifulSoup
from fortune_companies import EntityInfo
from utils import save2pickle

"""The following methods applies to 2015-2018 data, the previous years, check the methodology
    can be referred to: https://github.com/cmusam/fortune500
"""
TOPN = 500
EXTRACT_YEAR = 2017
EXTRACT_LIST_URL = "http://fortune.com/fortune500/{year}/list"
PATH_DATA_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "data")
# open inspect and go to the Network panel, you can find a request as following format
YEAR_API_LINK = {
    2017: "http://fortune.com/api/v2/list/2013055/expand/item/ranking/asc/{start_rank}/100",
    2015: "http://fortune.com/api/v2/list/1141696/expand/item/ranking/asc/{start_rank}/100",
    2016: "http://fortune.com/api/v2/list/1666518/expand/item/ranking/asc/{start_rank}/100",
}

API_LINK_EXTRACT = YEAR_API_LINK[EXTRACT_YEAR]
entity_ranked = {}
for rank in range(0, TOPN, 100):
    page = requests.get(API_LINK_EXTRACT.format(start_rank=rank))
    soup = BeautifulSoup(page.content, "html.parser")
    page_json = page.json()
    page_list_entities = page_json["list-items"]
    for entity in page_list_entities:
        entity_extractor = EntityInfo(entity)
        entity_info = entity_extractor.entity_info
        if entity_info:
            id_entity = entity_info["id_company"]
            entity_ranked[id_entity] = entity_info
fname_fortune500_companies = os.path.join(PATH_DATA_FOLDER, "fortune500_{year}.pickle".format(year=EXTRACT_YEAR))
save2pickle(fname_fortune500_companies, entity_ranked)
