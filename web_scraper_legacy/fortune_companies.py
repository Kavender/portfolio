import numpy
from bs4 import BeautifulSoup
from utils import get_shortlink_from_url
from nlp_utils import convert_text_to_number, convert_text_to_bool


class EntityInfo(object):
    """From Fortune500 List, extract entity related information to build candidate pool
    """

    def __init__(self, entity_session={}):
        self.entity_info = {}
        self.entity_json = entity_session
        if self.entity_json:
            self.entity_meta_data = entity_session["meta"]
            self.set_entity_values()

    def set_entity_values(self):
        # could add class input params to select only extract correponding fields
        self.get_company_basic()
        self.get_company_location()
        self.get_company_financials()
        self.get_company_rankings()

    def get_company_basic(self):
        # company related photo: one_entity['thumbnail'], but it's not company logo
        # not analyzed right now, 'eeoc-lawsuit', 'most-recent-lawsuit-url'
        entity_id = self.entity_json["id"]
        entity_name = self.entity_json["title"]
        entity_descrip = BeautifulSoup(self.entity_json["description"], "lxml").text
        entity_logo = self.entity_json["companies"][0]["logo"]
        fortune_profile_link = self.entity_json["permalink"]
        entity_news = self.entity_json["related"]["news"]
        # basic from meta data
        full_name = self.entity_meta_data["fullname"]
        ticker = self.entity_meta_data["ticker"]
        num_employee = convert_text_to_number(self.entity_meta_data["employees"])
        sector = self.entity_meta_data["sector"]
        industry = self.entity_meta_data["industry"]
        url = get_shortlink_from_url(self.entity_meta_data["website"])
        basic_info = {
            "id_company": entity_id,
            "company": entity_name,
            "full_name": full_name,
            "ticker": ticker,
            "logo": entity_logo,
            "num_employee": num_employee,
            "sector": sector,
            "industry": industry,
            "url": url,
            "news": entity_news,
            "fortune_profile_link": fortune_profile_link,
            "description": entity_descrip,
        }
        return self.entity_info.update(basic_info)

    def get_company_location(self):
        address_name = "Headquarters"
        hq_city = self.entity_meta_data["hqcity"]
        hq_state = self.entity_meta_data["hqstate"]
        hq_street1 = self.entity_meta_data["hqaddr"]
        hq_street2 = numpy.nan
        hq_zip = self.entity_meta_data["hqzip"]
        location_info = {
            "address_name": address_name,
            "state": hq_state,
            "city": hq_city,
            "street1": hq_street1,
            "street2": hq_street2,
            "zip": hq_zip,
        }
        return self.entity_info.update(location_info)

    def get_company_financials(self):
        is_profitable = convert_text_to_bool(self.entity_meta_data["profitable"])
        market_val = convert_text_to_number(self.entity_meta_data["mktval"])
        revenue = convert_text_to_number(self.entity_meta_data["revenues"])
        profits = convert_text_to_number(self.entity_meta_data["profits"])
        eps = convert_text_to_number(self.entity_meta_data["eps"])
        financials = {
            "is_profitable": is_profitable,
            "mkt_val": market_val,
            "revenue": revenue,
            "profits": profits,
            "EPS": eps,
        }
        return self.entity_info.update(financials)

    def get_company_rankings(self):
        fortune_rank = convert_text_to_number(self.entity_meta_data["ranking"])
        prev_fortune_rank = convert_text_to_number(self.entity_meta_data["prevrank"])
        rank_global = convert_text_to_number(self.entity_meta_data["global500-rank"])
        rank_world = convert_text_to_number(self.entity_meta_data["change-the-world-rank"])
        rank_best = convert_text_to_number(self.entity_meta_data["best-companies-rank"])
        rank_fastest = convert_text_to_number(self.entity_meta_data["100-fastest-growing-companies-rank"])
        rank_admired = convert_text_to_number(self.entity_meta_data["worlds-most-admired-companies-rank"])
        rankings = {
            "fortune500": fortune_rank,
            "prev_fortune500": prev_fortune_rank,
            "global500": rank_global,
            "change_world": rank_world,
            "best_companies": rank_best,
            "fast_growing": rank_fastest,
            "most_admire": rank_admired,
        }
        return self.entity_info.update(rankings)
