import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import web

from apis import APIError


# 以下两个函数为url的处理函数：
def get(path):
	'''
	Define decorator @get('/path')
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__='GET'
		wrapper.__route__=path
		return wrapper
	return decorator

def post(path):
	'''
	Define decorator @post('/path')
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__='POST'
		wrapper.__route__=path
		return wrapper
	return decorator

# 以下四个函数用于获取url中的参数：
def get_required_kw_args(fn):
	args=[]
	params=inspect.signature(fn).parameters				#inspect是第三方库里直接调用的
	for name,param in params.items():
		if param.kind==inspect.Parameter.KEYWORD_ONLY and param.default==inspect.Parameter.empty:
			args.append(name)
	return tuple(args)
	# pass

def get_named_kw_args(fn):
	args=[]
	params=inspect.signature(fn).parameters
	for name in params.items():
		if param.kind==inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
		# pass
	return tuple(args)
	# pass

def has_named_kw_args(fn):
	params=inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind==inspect.Parameter.KEYWORD_ONLY:
			return True

def  has_var_kw_arg(fn):
	params=inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind==inspect.Parameter.VAR_KEYWORD:
			return True
	# pass

def has_request_arg(fn):
	sig=inspect.signature(fn)
	params=sig.parameters
	found=False
	for name,param in params.items():
		if name=='request':
			found=True
			continue
		if found and (param.kind!=inspect.Parameter.VAR_POSITIONAL and param.kind!=inspect.Parameter.KEYWORD_ONLY and param.kind!=inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function:%s%s'%(fn.__name__,str(sig)))			#参数不符合任意一种类型的时候抛出错误
	return found
	# pass

class RequestHandler(object):
	# __init__的参数不完整，记得补完
	def __init__(self, app,fn):
		
		self.app = app
		self.fn=fn
		# 补充其他参数：
		self.has_request_arg=has_request_arg(fn)
		self.has_var_kw_arg=has_var_kw_arg(fn)
		self.has_named_kw_args=has_named_kw_args(fn)
		self._named_kw_args=get_named_kw_args(fn)
		self._required_kw_args=get_required_kw_args(fn)

	@asyncio.coroutine
	def __call__(self,request):
		kw=None 			#kw的作用，可以理解为用来保存用户注册的数据
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:		#如果三个中至少有一个不为none，则执行以下语句，否则跳到kw=none的情况
			if request.method =="POST":				#在这里post和get两种方法分开判断了，因为post是用来处理用户输入的数据的(比如创建用户时，输入的用户名，邮箱地址等)
				if not request.content_type:
					return web.HTTPBadRequest('Missing Content-Type.')
				ct= request.content_type.lower()
				if ct.startswith('application/json'):
					params= yield from request.json()
					if not isinstance(params,dict):
						return web.HTTPBadRequest('JSON body must be object.')
					kw=params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params= yield from request.post()
					kw= dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
			if request.method =='GET':				#GET用来处理带参数的url
				qs= request.query_string
				if qs:
					kw= dict()
					for k,v in parse.parse_qs(qs, True).items():
						kw[k]=v[0]
		if kw is None:
			kw= dict(**request.match_info)
		else:
			if not self.has_var_kw_arg and self._named_kw_args:			#如果出现了多余的参数(比如用户名，密码，邮箱以外不必要的参数)，就把它去掉
				# remove all unamed kw:
				copy=dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name]=kw[name]
				kw=copy
				# check named arg：
			for k,v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args: %s'%k)
				kw[k]=v
		if self._has_request_arg:			#构建request实例
			kw['request']=request
		if self._required_kw_args:			#再检查一遍参数
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest('Missing argument: %s'% name)
		logging.info('call with args: %s'% str(kw))			#把参数传入fn
		try:
			r=yield from self.__func(**kw)
			return r
		except APIError as e:
			return dict(error =e.error, data= e.data, message=e.message)

# 处理静态文件：
def add_static(app):
	# pass
	path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	app.router.add_static('/static/',path)
	logging.info('add static %s => %s' % ('/static/',path))

def add_route(app,fn):
			# pass
			method=getattr(fn,'__method__',None)
			path=getattr(fn,'__route__',None)
			if path is None or method is None:
				raise ValueError('@get or @post not defined in %s.'%str(fn))
			if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
				fn=	asyncio.coroutine(fn)
			logging.info('add route %s %s => %s(%s)' %(method,path,fn.__name__,','.join(inspect.signature(fn).parameters.keys())))			#以装饰器的方式给url处理函数加上method和path属性
			app.router.add_route(method,path,RequestHandler(app,fn))			#真正的注册语句在这里

# add_routes函数用循环的方式来批量注册url的处理函数，就不用调用add_route一个个注册了
def add_routes(app,module_name):
	'''
    n是'.'最后出现的位置 
    如果为-1，说明是 module_name中不带'.',例如(只是举个例子) handles 、 models 
    如果不为-1,说明 module_name中带'.',例如(只是举个例子) aiohttp.web(n=7) 、 urlib.parse()(n=5) 
    我们在app中调用的时候传入的module_name为handles,不含'.',if成立, 动态加载module 
    '''  
	n=module_name.rfind('.')
	if n==(-1):			#n=-1,说明不含'.',动态加载该module
		mod=__import__(module_name,globals(),locals())
	else:				#module_name中含'.'的情况
		'''
		举个例子，假设有一个aaa.bbb类型，我们需要从aaa中加载bbb；
		'''
		name=module_name[n+1:]			#得到bbb
		mod=getattr(__import__(module_name[:n],globals(),locals(),[name]),name)			#加载
	# 用for循环注册url的所有处理函数：
	for attr in dir(mod):			
		if attr.startwith('_'):
			continue
		fn=getattr(mod,attr)
		if callable(fn):
			method=getattr(fn,'__method__',None)
			path=getattr(fn,'__route__',None)
			# 注册函数fn。如果fn不是url处理函数，那么method为None,这一步直接跳过(不注册)进入下一个循环
			if method and path:			
				add_route(app,fn)

