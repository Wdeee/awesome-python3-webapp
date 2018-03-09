import asyncio




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



class RequestHandler(object):
	# __init__的参数不完整，记得补完
	def __init__(self, app,fn):
		
		self.app = app
		self.fn=fn
		# ......

	@asyncio.coroutine
	def __call__(self,request):
		# kw=....获取参数
		r=yield from self.__func(**kw)
		return r

		