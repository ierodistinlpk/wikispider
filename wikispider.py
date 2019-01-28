#!/usr/bin/python3

import requests
import asyncio
import logging,sys
from bs4 import BeautifulSoup
from collections import deque
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dbstruct import Page, Link
#from sqlite3 import dbapi2 as sqlite

logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])

class WikiSpider:
    encoding = 'utf-8'
    root_div = ''
#    scraper = BeautifulScraper()
    depth=1
    link_queue=deque([])
    baseurl=''
    page_limit=3
    alchemy_session=None
    loop=None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:63.0) Gecko/20100101 Firefox/63.0'
      }
    
    def __init__(self, encoding='utf-8', root_div="content", depth=2):
        self.encoding=encoding
        self.root_div = root_div
        self.depth=depth
        engine = create_engine('sqlite:///db.db', echo=True)
        #engine = create_engine('sqlite+pysqlite:///file.db', module=sqlite)
        self.alchemy_session = sessionmaker(bind=engine)()
        
    def get_page(self, url=None, depth=0):
        self.loop=asyncio.new_event_loop()
        first_task=self.loop.create_task(self._async_get_page(url, depth))
        self.loop.run_until_complete(first_task)
    
    async def _async_get_page(self, url, depth):
        if not self.baseurl:
            parsed_result=requests.utils.urlparse(url)
            self.baseurl=parsed_result.scheme+'://'+parsed_result.hostname
            logging.debug('base url is: %s', self.baseurl)            
        if (depth <= self.depth):
            page = BeautifulSoup(requests.get(url, headers=self.headers).text,'html.parser')            
            body = page.find('div',id=self.root_div) if self.root_div else page.body
            page_title=page.title
            links = body.find_all('a')
            page_limit=0
            last_task=None
            for link in links:
                if link.has_attr('href') and '#' not in link['href']:
                    if self.page_limit and (page_limit > self.page_limit):
                        break
                    page_limit+=1
                    link_url=link['href'] if self.baseurl in link['href'] else self.baseurl + link['href']
                    link_title=link.string
                    last_task=self.loop.create_task(self._async_get_page(link_url,depth+1))
                    self.record_url_and_link(url,page_title,link_url,link_title,depth)
                    #self.link_queue.append({'href':link['href'],'depth':depth+1})
            await last_task
        else:
            pass

    ## save link to db - TODO
    def record_url_and_link(self,url,page_title,link_url,link_title,depth):
        self.alchemy_session.add(Page(url=url,title=page_title))
        self.alchemy_session.add(Link(from_page=url,title=link_title,href=link_url,depth=depth))
        
        logging.info('find link at %s %s: %s',depth, url, link_url)
