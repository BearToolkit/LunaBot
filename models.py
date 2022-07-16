import datetime
from contextlib import closing
import copy

def utcnow():
  return datetime.datetime.utcnow()

class Model:
  def create(self, content):
    message = dict()
    for key in self.default_attributes.keys():
      if key in content.keys():
        message[key] = content[key]
      else:
        message[key] = self.default_attributes[key]()
    
    columns = ', '.join(message.keys())
    named_map = ':' + ', :'.join(message.keys())

    query_string = '''
    INSERT INTO {} 
    ({})
    VALUES
    ({});
    '''.format(self.table_name, columns, named_map)

    return query_string, message

  def delete(self, where):
    values = []
    conditions = []
    for key in where.keys():
      if key in self.default_attributes.keys():
        conditions.append(key + where[key][0] + ':' + key)
        values.append(where[key][1])

    query_string = '''
    DELETE FROM {} 
    WHERE ({})
    '''.format(self.table_name, ', '.join(conditions))

    return query_string, values

  def find(self, where=None, order=None, limit=None):
    values = []
    query_string = '''
    SELECT * FROM {} 
    '''.format(self.table_name)

    if where:
      conditions = []
      for key in where.keys():
        if key in self.default_attributes.keys():
          conditions.append(key + where[key][0] + ':' + key)
          values.append(where[key][1])

      query_string += '''
      WHERE ({})
      '''.format(', '.join(conditions))

    if order:
      query_string += '''
      ORDER BY {} {}
      '''.format(order[0], order[1])
    
    if limit:
      query_string += '''
      LIMIT {}
      '''.format(limit)
    
    return query_string, values
  
  def formatResult(self, result):
    formattedResult = copy.deepcopy(self.default_attributes)

    i = 0
    for key in self.default_attributes.keys():
      defaultType = self.default_attributes[key]()
      if type(defaultType) == datetime.datetime:
        formattedResult[key] = datetime.datetime.fromisoformat(result[i])
      elif type(defaultType) == str:
        formattedResult[key] = result[i]
      elif type(defaultType) == bool:
        formattedResult[key] = bool(result[i])
      i += 1

    return formattedResult

class Messages(Model):
  table_name = 'Messages'

  default_attributes = {
    'Timestamp': utcnow,
    'Message': str,
    'User': str,
    'ID': str
  }
  
  def __init__(self, conn):
    create_table_query = '''
      CREATE TABLE IF NOT EXISTS Messages (
        Timestamp DATE,
        Message TEXT,
        User TEXT,
        ID INTEGER PRIMARY KEY
      );
    '''
    with closing(conn.cursor()) as cursor:
      cursor.execute(create_table_query)
    conn.commit()

class Members(Model):
  table_name = 'Members'

  default_attributes = {
    'JoinAt': utcnow,
    'Verified': bool,
    'ID': str
  }
  
  def __init__(self, conn):
    create_table_query = '''
      CREATE TABLE IF NOT EXISTS Members (
        JoinAt DATE,
        Verified BOOLEAN,
        ID INTEGER PRIMARY KEY
      );
    '''
    with closing(conn.cursor()) as cursor:
      cursor.execute(create_table_query)
    conn.commit()