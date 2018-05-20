from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Catalog, Base

engine = create_engine('sqlite:///catalogapp.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

catalog1 = Catalog(name='Soccer')

session.add(catalog1)
session.commit()

catalog2 = Catalog(name='Basketball')

session.add(catalog2)
session.commit()

catalog3 = Catalog(name='Baseball')

session.add(catalog3)
session.commit()

catalog4 = Catalog(name='Snowboarding')

session.add(catalog4)
session.commit()

catalog5 = Catalog(name='Rock Climbing')

session.add(catalog5)
session.commit()

catalog6 = Catalog(name='Football')

session.add(catalog6)
session.commit()

catalog7 = Catalog(name='Scating')

session.add(catalog7)
session.commit()

catalog8 = Catalog(name='Hockey')

session.add(catalog8)
session.commit()


print "added menu items!"
