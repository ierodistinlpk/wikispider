from wikispider import WikiSpider as ws
from dbstruct import Page, Link
#init
w=ws()

#extract
w.get_page('https://en.wikipedia.org/wiki/Main_Page',wipe_old=True, depth=6)

#check result
pages_count=w.alchemy_session.query(Page).count() #execute('select count(*) from pages')
print ("total pages grabbed: {0}".format(pages_count)) 

links_count=w.alchemy_session.query(Link).count() #execute('select count(*) from pages')
print ("total links found: {0}".format(links_count)) 
