from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import datetime

Base = declarative_base()


class ErrorLog(Base):
    __tablename__ = 'error_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    uid = Column(String(36))
    description = Column(String)


engine = create_engine('sqlite:///error_logs.db')

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def log_error(uid, description):
    error_log = ErrorLog(uid=uid, description=description)
    session.add(error_log)
    session.commit()
