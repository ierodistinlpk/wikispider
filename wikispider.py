#!/usr/local/bin/python3.7

import requests
import asyncio
import logging,sys
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from dbstruct import Page, Link

log_level=logging.DEBUG
#log_level=logging.INFO
#log_level=logging.WARNING

logging.basicConfig(level=log_level, handlers=[logging.StreamHandler(sys.stdout)])

class WikiSpider:
    ''' 
    Wiki Spider parses site and stores page-links relation to sqlite
    * constructor parameters:
        root div: default is 'content' for mediawiki. Set '' to parse all page. Set div element is to parse inside specified div
        encoding: default is utf-8. Set any if need
    * get_page parameters:
        url: start url for parsing. No default value.
        depth: default is 2. set any that you need
        wipe_old: default False. Wipes old tables (I hope) before start parsing
    '''

    encoding = 'utf-8'
    root_div = ''
    depth=0
    baseurl=''
    page_limit=3 # for test and debug. zero means all pages
    engine=None
    alchemy_session=None
    db_records=0
    loop=None
    sem=None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:63.0) Gecko/20100101 Firefox/63.0'
      }
    
    def __init__(self, encoding='utf-8', root_div="content"):
        self.encoding=encoding
        self.root_div = root_div
        self.engine = create_engine('sqlite:///db.db', echo=True)
        self.alchemy_session = sessionmaker(bind=self.engine,autoflush=True)()
        
    def get_page(self, url=None, depth=2, wipe_old=False):
        self.depth=depth
        self._prepare_tables(wipe_old)
        self.loop=asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.sem=asyncio.Semaphore(5)
        first_task=self.loop.create_task(self._async_get_page(url, 0))
        self.loop.run_until_complete(first_task)
        self.alchemy_session.commit()
        self.alchemy_session.close()
        
    def _prepare_tables(self,wipe_old):
        for table in [Page, Link]: 
            if wipe_old:
                logging.debug('dropping table: %s', table)            
                table.metadata.drop_all(self.engine)
            if not self.engine.has_table(table.__table__.name):
                logging.debug('creating table: %s', table)            
                table.metadata.create_all(self.engine)
            
    async def _async_get_page(self, url, depth):
        logging.debug('entering page: %s, %s/%s', url, depth.__str__(), self.depth.__str__())
        if not self.baseurl:
            parsed_result=requests.utils.urlparse(url)
            self.baseurl=parsed_result.scheme+'://'+parsed_result.hostname
            logging.debug('base url is: %s', self.baseurl)            
        if (depth <= self.depth):
            logging.debug('entering page: %s, %s/%s', url, depth.__str__(), self.depth.__str__())
            req_page=requests.get(url, headers=self.headers)
            if req_page.status_code == 200:
                await self.sem.acquire()
                page = BeautifulSoup(req_page.text,'html.parser')            
                body = page.find('div',id=self.root_div) if self.root_div else page.body
                page_title=page.title.string
                logging.warning('got page: %s, %s', url, page_title)
                self._record_page(url,page_title)
                links = body.find_all('a')
                page_limit=0
                child_tasks=[]
                for link in links:
                    if link.has_attr('href') and '#' not in link['href']:
                        if self.page_limit and (page_limit > self.page_limit):
                            break
                        page_limit+=1
                        link_url=link['href'] if self.baseurl in link['href'] else self.baseurl + link['href']
                        link_title=link.string
                        self._record_link(url,link_url,link_title,depth)
                        child_tasks.append(self.loop.create_task(self._async_get_page(link_url,depth+1)))
                self.sem.release()
                for task in child_tasks:
                    await task
            else:
                logging.error('url %s returned status %s, skipped', url, req_page.status_code.__str__)
        else:
            pass

    ## save link to db - TODO
    def _record_page(self,url,page_title):
        self.alchemy_session.merge(Page(url=url,title=page_title))
        self.db_records+=1
        if self.db_records>100:
            self.alchemy_session.commit()
            self.alchemy_session.clear()
            self.db_records-=100

    def _record_link(self,url,link_url,link_title,depth):
        if not link_title:
            link_title='<no>'
        self.db_records+=1
        self.alchemy_session.merge(Link(from_page=url,title=link_title,href=link_url,depth=depth))

