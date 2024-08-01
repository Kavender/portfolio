import re
import random
import textwrap
import hashlib
from collections import OrderedDict
from http import cookiejar
from urllib import request, error
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen
from bs4 import BeautifulSoup
from constants import USER_AGENT_LIST, REGEX_DIV, REGEX_JOB_KEYWORDS
from utils import build_url_variants
from utils.normalize import remove_multiple_spaces


def line_content_wrapper(text):
    dedented_text = textwrap.dedent(text).strip()
    rm_breaker = re.sub(r"(?<=[a-z])\r?\n", " ", dedented_text)
    rm_breaker = rm_breaker.replace("\n", " ").replace("\r", "")
    str_text = remove_multiple_spaces(rm_breaker)
    return str_text


class HtmlParser(object):
    def __init__(self):
        user_agent = random.choice(USER_AGENT_LIST)
        self.headers = {"User-Agent": user_agent}
        self.proxy = None  # data=None

    def url_opener(self, url):
        try:
            req = request.Request(url, headers=self.headers)
            cookie = cookiejar.CookieJar()
            cookie_process = request.HTTPCookieProcessor(cookie)
            opener = request.build_opener()
            if self.proxy:
                proxies = {urlparse(url).scheme: self.proxy}
                opener.add_handler(request.ProxyHandler(proxies))
            return opener.open(req)
        except error.URLError as e:
            print("HtmlDownLoader download error:", e.reason)
        return None

    def page_downloader(self, url, retry_count=3):
        url_opened = self.url_opener(url)
        try:
            content = url_opened.read()
        except error.URLError as e:
            if retry_count > 0:
                if hasattr(e, "code") and 500 <= e.code < 600:
                    return self.page_downloader(url, retry_count - 1)
        return content


def parse(url, content, html_encode="utf-8"):
    if (url is None) or (content is None):
        return None
    soup = BeautifulSoup(content, "html.parser", from_encoding=html_encode)
    return soup


def get_job_urls(soup, url):
    job_links = {}
    links = soup.find_all("a", href=re.compile(r"/careers/\w+"))
    for link in links:
        link_text = link.get_text(strip=True)
        link_text = line_content_wrapper(link_text)
        url_path = link["href"]
        job_link = urljoin(url, url_path)
        job_links.setdefault(link_text, set()).add(job_link)
    return job_links


def collect_job_opening_with_company_url(page_parser, company_url):
    company_job_links = {}
    target_page_urls = build_url_variants(url)
    page_searched = []
    for target_url in target_page_urls:
        if target_url in page_searched:
            continue
        try:
            url2open = page_parser.url_opener(target_url)
            url_redirect = url2open.geturl()
            page_searched.append(url_redirect)
            content = page_parser.page_downloader(url_redirect)
            soup = BeautifulSoup(content, "html.parser", from_encoding="utf-8")
            page_job_links = get_job_urls(soup, url)
            if len(page_job_links) >= 3:
                for position in page_job_links:
                    position_links = page_job_links[position]
                    company_job_links[position] = company_job_links.get(position, set()).union(position_links)
        except:
            print("not about careers:", target_url)
    return company_job_links


def get_job_content(soup):
    all_paragraphs = soup.find_all("p")
    all_divisions = soup.find_all("div", {"class": lambda x: REGEX_DIV})
    job_content = OrderedDict()
    descrip_words = 0
    for div in all_divisions:
        paragraphs = div.find_all("p")
        list_items = div.find_all("li", text=REGEX_JOB_KEYWORDS)
        div_items = paragraphs + list_items
        for item in div_items:
            # text = get_text(paragraph)
            text = line_content_wrapper(item.get_text(strip=True))
            text_words = len(text.split())
            if text_words > 5:
                hash_text = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
                job_content[hash_text] = text
                descrip_words += len(text.split())

    if descrip_words <= 50:
        for paragraph in all_paragraphs:
            # text = get_text(paragraph)
            text = line_content_wrapper(paragraph.get_text(strip=True))
            text_words = len(text.split())
            if text_words > 5:
                hash_text = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
                job_content[hash_text] = text
                descrip_words += text_words
    return job_content


def collect_job_opening_content(page_parser, job_url):
    try:
        url2open = page_parser.url_opener(job_url)
        url_redirect = url2open.geturl()
        content = page_parser.page_downloader(url_redirect)
        soup = BeautifulSoup(content, "html.parser", from_encoding="utf-8")
        page_job = get_job_content(soup)
        return page_job
    except:
        print("not about job content:", job_url)
        return None


if __name__ == "__main__":
    url = "https://www.mineraltree.com/"
    job_url = "https://www.mineraltree.com/about-us/careers/account-executive"
    page_parser = HtmlParser()
    # company_job_links = collect_job_opening_with_company_url(page_parser, url)
    # for p in company_job_links:
    #     print(p, "-?", company_job_links[p])
    #     print("---------")
    job_content = collect_job_opening_content(page_parser, job_url)
    for hashed_line in job_content:
        print("row:", job_content[hashed_line])
        print("---")
