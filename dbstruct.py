from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base()

class Link(Base):
    __tablename__='links'

    from_page=Column(String, primary_key=True)
    href=Column(String, primary_key=True)
    title=Column(String)
    depth=Column(Integer)
    
    def __repr__(self):
        return "<href='{0}', title='{1}'>".format(self.href,self.title)

class Page(Base):
    __tablename__='pages'

    title=Column(String)
    url=Column(String,primary_key=True)
    
    def __repr__(self):
        return "<PAge: title='{0}'>".format(self.title)
