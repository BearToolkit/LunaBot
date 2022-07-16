import sqlite3 
import os, sys

from multiprocessing import Process, Lock
from contextlib import closing
import asyncio

from models import *

class Manager:
  models = []

  def __init__(self, filename):
    self.__lock = Lock()
    self.__conn = sqlite3.connect(filename)
    self.models.append(Messages(self.__conn))
    self.models.append(Members(self.__conn))
    
  async def insertRecord(self, table, record):
    self.__lock.acquire()

    try:
      for model in self.models:
        if table == model.table_name:
          query, values = model.create(record)
          with closing(self.__conn.cursor()) as cursor:
            cursor.execute(query, values)
          self.__conn.commit()

    except Exception as e:
      print(e)

    finally:
      self.__lock.release()

  async def delete(self, table, where):
    self.__lock.acquire()

    try:
      for model in self.models:
        if table == model.table_name:
          query, values = model.delete(where)
          with closing(self.__conn.cursor()) as cursor:
            cursor.execute(query, values)
          self.__conn.commit()

    except Exception as e:
      print(e)

    finally:
      self.__lock.release()

  async def findAll(self, table, where=None, order=None):
    self.__lock.acquire()
    try:
      for model in self.models:
        if table == model.table_name:
          query, values = model.find(where=where, order=order)
          print(query)
          with closing(self.__conn.cursor()) as cursor:
            cursor.execute(query, values)
            result = cursor.fetchall()
          self.__conn.commit()
          
          if result:
            for i in range(len(result)):
              result[i] = model.formatResult(result[i])
      
      return result

    except Exception as e:
      print(e)

    finally:
      self.__lock.release()

  async def findOne(self, table, where=None, order=None):
    self.__lock.acquire()
    try:
      for model in self.models:
        if table == model.table_name:
          query, values = model.find(where=where, order=order, limit=1)
          with closing(self.__conn.cursor()) as cursor:
            cursor.execute(query, values)
            result = cursor.fetchall()
          self.__conn.commit()

          if result:
            result = model.formatResult(result[0])
      
      return result

    except Exception as e:
      print(e)

    finally:
      self.__lock.release()