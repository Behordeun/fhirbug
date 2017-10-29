import os
import importlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

import settings
from server.requestparser import parse_url

# Create the db connection
os.environ["NLS_LANG"] = "GREEK_GREECE.AL32UTF8"
engine = create_engine(settings.SQLALCHEMY_CONFIG['URI'])
session = scoped_session(sessionmaker(bind=engine))

# Provide the base class for AbstractBaseClass to inherit
# You must do this BEFORE importing any models
Base = declarative_base()
Base.query = session.query_property()

import models  # Don't do from models import bla, stuff will break


def main():
  # pat = session.query(models.Patient).first()
  # pat = models.Patient.query.first()
  pat = models.Patient.get(940)

  # print(pat.to_fhir().as_json())
  print(pat)

  o = models.ProcedureRequest.get(16, contained=['subject'])
  print(o)

def handle_get_request(url):
  print('url', url)
  query = parse_url(url)
  resource = query.resource
  try:
    Resource = getattr(models, resource)
  except Exception as e:
    return {'error': 'resource does not exist'}, 400
  return Resource.get(query=query), 200


if __name__ == '__main__':
  main()
