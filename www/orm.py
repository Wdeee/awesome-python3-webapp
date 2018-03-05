# 需要注意的一点是，书上给的代码的顺序是乱的，而且不完整，需要自己根据调用的先后顺序和调用内容进行修改和补充

import asyncio, logging

import aiomysql

def log(sql, args=()):
	logging.info('SQL: %s' % sql)


# 创建连接池：
@asyncio.coroutine
def create_pool(loop,**kw):
	logging.info('create database connection pool...')
	global __pool
	__pool=yield from aiomysql.create_pool(
		host=kw.get('host','localhost'),
		port=kw.get('port',3306),
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset','utf8'),
		autocommit=kw.get('autocommit',True),
		maxsize=kw.get('maxsize',10),
		minsize=kw.get('minsize',1),
		loop=loop
	)

# SELECT:
@asyncio.coroutine
def select(sql,arqs,size=None):
	log(sql,args)
	global __pool
	with(yield from __pool) as conn:
		cur=yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?','%s'),args or ())
		if size:
			rs=yield from cur.fetchmany(size)
		else:
			re=yield from cur.fetchall()
		yield from cur.close()
		logging.info('rows returned: %s'%len(rs))
		return rs

# insert,update,delete语句:
@asyncio.coroutine
def execute(sql,args):											#使用一个通用的execute函数来执行这三种语句
	log(sql)
	with(yield from __pool) as conn:
		try:
			cur=yield from conn.cursor()
			yield from cur.execute(sql.replace('?','%s'),args)
			affected=cur.rowcount
			yield from cur.close()
		except BaseException as e:
			raise
		return affected


def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)



# 定义Model：
# class Model(dict, metaclass=ModelMetaclass):

# 	def __init__(self,**kw):
# 		super(Model,self).__init__(**kw)

# 	def __getattr__(self,key):
# 		try:
# 			return self[key]
# 		except KeyError:
# 			raise AttributeError(r"'Model' object has no attribute '%s'"%key)

# 	def __setattr__(self,key,value):
# 		self[key]=value

# 	def getValue(self,key):
# 		return getattr(self,key,None)

# 	def getValueOrDefault(self,key):
# 		value=getattr(self,key,None)
# 		if value is None:
# 			field=self.__mappings__[key]
# 			if field.default is not None:
# 				value=field.default() if callable(field.default) else field.default
# 				logging.debug('using default value for %s:%s'%(key,str(value)))
# 				setattr(self,key,value)
# 		return value

	# @classmethod
	# @asyncio.coroutine
	# def find(cls,pk):
	# 	'find object by primary key'
	# 	rs=yield from select('%s where `%s`=?'%(cls.__select__,cls.__primary_key__),[pk],1)
	# 	if len(rs)==0:
	# 		return None
	# 	return cls(**rs[0])

# 定义Field：
class Field(object):
	"""docstring for Field"""
	def __init__(self, name,column_type,primary_key,default):
		self.name=name
		self.column_type= column_type
		self.primary_key=primary_key
		self.default=default

	def __str__(self):
		return '<%s, %s:%s>' %(self.__class__.__name__, self.column_type, self.name)

# 定义映射varchar的StringField:
class StringField(Field):

	def __init__(self, name=None,primary_key=False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)
		# self.arg = arg

# 参考源代码里给出的其他Filed子类的定义：
class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

# 定义ModelMetaclass:
class ModelMetaclass(type):

	def __new__(cls, name,bases,attrs):
		if name=='Model':
			return type.__new__(cls,name,bases,attrs)
		tableName=attrs.get('__table__',None) or name
		logging.info('found model: %s(table %s)'%(name,tableName))
		mappings=dict()
		fields=[]
		primaryKey=None
		for k,v in attrs.items():
			if isinstance(v,Field):
				logging.info('found mapping: %s ==> %s'%(k,v))
				mappings[k]=v
				if v.primary_key:
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field: %s'%k)
					primaryKey=k
				else:
					fields.append(k)
		if not primaryKey:
			raise RuntimeError('Primmary key not found.')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields=list(map(lambda f: '`%s`' %f,fields))
		attrs['__mappings__']=mappings
		attrs['__table__']=tableName
		attrs['primary_key']=primaryKey
		# 构造默认的select，insert，updated和delete语句：
		attrs['__select__']='select `%s`, %s from `%s`' %(primaryKey,','.join(escaped_fields),tableName)
		# attrs['__insert__']='insert into `%s` (%s, `%s`) values (%s)' %(tableName,','.join(escaped_fields),primaryKey,create_args_string(len(escaped_fields) + 1))
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__']='update `%s` set %s where `%s`=?' %(tableName,','.join(map(lambda f:'`%s`=?'%(mappings.get(f).name or f), fields)),primaryKey)
		attrs['__delete__']='delete from `%s` where `%s`=?'%(tableName,primaryKey)
		return type.__new__(cls,name,bases,attrs)

class Model(dict,metaclass=ModelMetaclass):						#定义Model应该放在最后

	def __init__(self,**kw):
		super(Model,self).__init__(**kw)

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'"%key)

	def __setattr__(self,key,value):
		self[key]=value

	def getValue(self,key):
		return getattr(self,key,None)

	def getValueOrDefault(self,key):
		value=getattr(self,key,None)
		if value is None:
			field=self.__mappings__[key]
			if field.default is not None:
				value=field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s:%s'%(key,str(value)))
				setattr(self,key,value)
		return value

	# ...

	@classmethod
	@asyncio.coroutine
	def find(cls,pk):
		'find object by primary key'
		rs=yield from select('%s where `%s`=?'%(cls.__select__,cls.__primary_key__),[pk],1)
		if len(rs)==0:
			return None
		return cls(**rs[0])
		# user=yield from User.find('9595')

	# 实例中会用到的findAll:
	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		' find objects by where clause. '
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit', None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit, int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:
				sql.append('?, ?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value: %s' % str(limit))
		rs = await select(' '.join(sql), args)
		return [cls(**r) for r in rs]

	@classmethod
	async def findNumber(cls, selectField, where=None, args=None):
		' find number by select and where. '
		sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']





	@asyncio.coroutine
	def save(self):
		args=list(map(self.getValueOrDefault,self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows=yield from execute(self.__insert__,args)
		if rows!=1:
			logging.warn('failed to insert record: affected rows: %s'%rows)
			
# user=User(id=9595,name='Dee')
# yield from user.save()


# #ORM：
# from orm import Model, StringField, IntegerField

# class User(Model):
# 	__table__='users'

# 	id=IntegerField(primary_key=True)
# 	name=StringField()

# # 创建实例：
# user=User(id=9595,name='Dee')
# user.insert()							#存入数据库				#这个实例好像写的有点小问题，insert老是报错，放到源代码里也跑不通
# users=User.findAll()					#查询所有User对象
