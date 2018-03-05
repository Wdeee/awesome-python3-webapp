# 需要注意的一点是，书上给的代码的顺序是乱的，而且不完整，需要自己根据调用的先后顺序和调用内容进行修改和补充

import asyncio, logging

import aiomysql

# import logging; logging.basicConfig(level=logging.INFO)

# import asyncio, os, json, time
# from datetime import datetime

# from aiohttp import web

# def index(request):
# 	# return web.Response(body=b'<h1>Awesome</h1>')
# 	return web.Response(body=b'<h1>Awesome</h1>', headers={'content-type':'text/html'})				#如果body是二进制的时候，要在后面加上content-type为text/html(文本)，不然会变成下载操作。

# @asyncio.coroutine
# def init(loop):
# 	app=web.Application(loop=loop)
# 	app.router.add_route('GET','/',index)
# 	srv=yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
# 	logging.info('server started at http://127.0.0.1:9000...')
# 	return srv

# 设置logging的调试级别(info级)，如果不设置等于pass
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
		autocommit=kw.get('autocommit',True),			#是否自动提交事务,在增删改数据库数据时,如果为True,不需要再commit来提交事务了
		maxsize=kw.get('maxsize',10),
		minsize=kw.get('minsize',1),
		loop=loop
	)

# SELECT:
# 该协程封装的是查询事务,第一个参数为sql语句,第二个为sql语句中占位符的参数列表,第三个参数是要查询数据的数量
@asyncio.coroutine
def select(sql,arqs,size=None):
	log(sql,args)					#这些log都是在调用上面的调试级别函数
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

# # 以上select代码的等效写法，用await和acquire代替yield from。但是要注意函数的定义方法也要相应改变(@asyncio.coroutine改成async)
# async def select(sql,arqs,size=None):
# 	log(sql,args)
# 	global __pool
# 	async with __pool.acquire() as conn:
# 		async with conn.cursor(aiomysql,DictCursor) as cur:
# 			await cur.execute(sql.replace('?','%s'),args or ())
# 			if size:
# 				rs=await cur.fetchmany(size)
# 			else:
# 				re=await cur.fetchall()
# 			logging.info('rows returned: %s'%len(rs))
# 			return rs


# insert,update,delete语句:
@asyncio.coroutine
def execute(sql,args):				#使用一个通用的execute函数来执行这三种语句
	log(sql)
	with(yield from __pool) as conn:
		try:
			cur=yield from conn.cursor(aiomysql,DictCursor)
			yield from cur.execute(sql.replace('?','%s'),args)
			affected=cur.rowcount
			yield from cur.close()
		except BaseException as e:
			if not autocommit:
				yield from conn.rollback()			#回滚,在执行commit()之前如果出现错误,就回滚到执行事务前的状态,以免影响数据库的完整性
			raise
		return affected

# 创建拥有几个占位符的字符串
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

# 定义Field：
# 该类是为了保存数据库列名和类型的基类
class Field(object):

	def __init__(self, name,column_type,primary_key,default):
		self.name=name
		self.column_type= column_type
		self.primary_key=primary_key
		self.default=default

	def __str__(self):
		return '<%s, %s:%s>' %(self.__class__.__name__, self.column_type, self.name)

# 以下几种是具体的列名的数据类型
# 定义映射varchar的StringField:
class StringField(Field):

	def __init__(self, name=None,primary_key=False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)					#super函数是子类调用父类的函数。这里用super调用了父类的__init__

# 参考源代码里给出的其他Filed子类的定义：
class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)				#源代码里直接把primary_key值赋成False，不过不赋值也是跑得通的
        # super().__init__(name, 'boolean', primary_key, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)
        # super().__init__(name, 'boolean', primary_key, default)

# 定义ModelMetaclass:
class ModelMetaclass(type):

	def __new__(cls, name,bases,attrs):
		if name=='Model':
			return type.__new__(cls,name,bases,attrs)			#如果是基类，不做处理直接返回
		tableName=attrs.get('__table__',None) or name
		logging.info('found model: %s(table %s)'%(name,tableName))
		mappings=dict()				#保存列类型的对象
		fields=[]					#保存列名的数组
		primaryKey=None
		for k,v in attrs.items():
			if isinstance(v,Field):				#如果是列名就保存下来
				logging.info('found mapping: %s ==> %s'%(k,v))
				mappings[k]=v
				if v.primary_key:
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field: %s'%k)
						# raise Error('Duplicate primary key for field: %s'%k)			#error类型不写也能跑通。或者写StandardError
					primaryKey=k
				else:
					fields.append(k)			#保存非主键的列名
		if not primaryKey:
			raise RuntimeError('Primary key not found.')
			# raise Error('Primary key not found.')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields=list(map(lambda f: '`%s`' %f,fields))
		attrs['__mappings__']=mappings
		attrs['__table__']=tableName
		attrs['primary_key']=primaryKey
		# 构造默认的select，insert，updated和delete语句：
		# 添加反引号``是为了避免和sql关键字冲突,否则sql语句会执行出错
		attrs['__select__']='select `%s`, %s from `%s`' %(primaryKey,','.join(escaped_fields),tableName)
		# attrs['__select__']='select %s, %s from %s' %(primaryKey,','.join(escaped_fields),tableName)			#去掉反引号，程序本身是跑的通，但估计真正到了应用sql的时候会出错
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__']='update `%s` set %s where `%s`=?' %(tableName,','.join(map(lambda f:'`%s`=?'%(mappings.get(f).name or f), fields)),primaryKey)
		attrs['__delete__']='delete from `%s` where `%s`=?'%(tableName,primaryKey)
		return type.__new__(cls,name,bases,attrs)


# 模型的基类,继承于dict,主要作用就是如果通过点语法来访问对象的属性获取不到的话,可以定制__getattr__来通过key来再次获取字典里的值
# 定义Model应该放在最后,因为调用了前面的ModelMetaclass
class Model(dict,metaclass=ModelMetaclass):

	def __init__(self,**kw):
		# super(Model,self).__init__(**kw)			#这是super函数一种比较老的写法
		super().__init__(**kw)

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'"%key)

	def __setattr__(self,key,value):
		self[key]=value

	def getValue(self,key):
		return getattr(self,key,None)			#调用getattr获取一个未存在的属性,也会走__getattr__方法,但是因为指定了默认返回的值,__getattr__里面的错误永远不会抛出

	def getValueOrDefault(self,key):
		value=getattr(self,key,None)
		if value is None:
			field=self.__mappings__[key]
			if field.default is not None:
				value=field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s:%s'%(key,str(value)))
				setattr(self,key,value)
		return value

	@classmethod			#@classmethod装饰器用于把类里面定义的方法声明为该类的类方法
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
	@asyncio.coroutine
	def findAll(cls, where=None, args=None, **kw):
	# async def findAll(cls, where=None, args=None, **kw):
		' find objects by where clause. '
		sql = [cls.__select__]
		# if where is None:			#我估计下面一句和这句等效？
		if where:					#如果where里给的条件成立，执行以下两句
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
		# rs = await select(' '.join(sql), args)					这里用await语法会有警告，所以换成了yield from的语法
		rs = yield from select(' '.join(sql), args)
		return [cls(**r) for r in rs]

	# 用装饰器和yield from写了一个findNumber：
	@classmethod
	@asyncio.coroutine
	def findNumber(cls, selectField, where=None, args=None):
		' find number by select and where. '
		sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = yield from select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']

	# 以下的都是对象方法,所以可以不用传任何参数,方法内部可以使用该对象的所有属性,及其方便
	# 保存实例到数据库：
	@asyncio.coroutine
	def save(self):
		args=list(map(self.getValueOrDefault,self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows=yield from execute(self.__insert__,args)
		if rows!=1:
			logging.warn('failed to insert record: affected rows: %s'%rows)

	# 更新数据库数据：
	@asyncio.coroutine
	def update(self):
		args=list(map(self.getValue,self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows=yield from execute(self.__update__,args)
		if rows!=1:
			logging.warn('failed to update by primary key: affected rows: %s'%rows)

	# 删除数据：
	@asyncio.coroutine
	def remove(self):
		args=list(self.getValue(self.__primary_key__))
		rows=yield from execute(self.__delete__,args)
		if rows!=1:
			logging.warn('failed to remove by primary key: affected rows: %s'%rows)



#ORM：
# 用户名是一个str，id是个整数类型
from orm import Model, StringField, IntegerField

class User(Model):
	__table__='users'

	id=IntegerField(primary_key=True)
	name=StringField()

# 创建实例：
user=User(id=9595,name='Dee')
user.update()							#存入数据库
# user.insert()							#原来写的是insert来存入数据库，但是Model并没有定义Insert这个方法，用的应该是update
users=User.findAll()					#查询所有User对象




# # #以下为测试
# 别人写的测试，跑了以后报错显示连不上Mysql...我是用户名记错了嘛。。。也有可能是数据库里没有myshcool这个东西
# loop = asyncio.get_event_loop()
# loop.run_until_complete(create_pool(host='127.0.0.1', port=3306,user='root', password='wl9595',db='mySchool', loop=loop))
# rs = loop.run_until_complete(select('select * from firstSchool',None))
# #获取到了数据库返回的数据
# print("heh:%s" % rs)
	
# user=User(id=9595,name='Dee')
# yield from user.save()