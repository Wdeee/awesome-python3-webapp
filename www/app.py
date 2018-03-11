import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import orm
from coroweb import add_routes, add_static

def init_jinja2(app, **kw):
	logging.info('init jinja2...')
	options=dict(
		autoescape= kw.get('autoescape',True),
		block_start_string= kw.get('block_start_string','{%'),
		block_end_string=kw.get('block_end_string','%}'),
		variable_start_string=kw.get('variable_start_string','{{'),
		variable_end_string=kw.get('variable_end_string','}}'),
		auto_reload=kw.get('auto_reload',True)
		)
	path= kw.get('path',None)
	if path is None:
		path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 template path: %s'%path)
	env= Environment(loader= FileSystemLoader(path), **options)
	filters= kw.get('filters',None)
	if filters is not None:
		for name, f in filters.items():
			env.filters[name]=f
	app['__templating__']=env


# middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。
# 一个middleware可以改变URL的输入、输出，甚至可以决定不继续处理而直接返回。
# middleware的用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方。

# 用来记录url日志的middleware:
# @asyncio.coroutine
# def logger_factory(app, handler):
# 	def logger(request):
# 		logging.info('Request: %s %s'%(request.method, request.path))		#记录日志
# 		# await asyncio.sleep(0.3)
# 		return (yield from handler(request))				#继续处理请求
# 	return logger
# 	# pass

async def logger_factory(app, handler):
	async def logger(request):
		logging.info('Request: %s %s'%(request.method, request.path))		#记录日志
		# await asyncio.sleep(0.3)
		return (await handler(request))				#继续处理请求
	return logger

# @asyncio.coroutine
# def  data_factory(app, handler):
# 	def parse_data(request):
# 		if request.method=='POST':
# 			if request.content_type.startswith('applicaiton/json'):
# 				request.__data__= yield from request.json()
# 				logging.info('request json: %s'%str(request.__data__))
# 			elif request.content_type.startswith('applicaiton/x-www-form-urlencoded'):
# 				request.__data__=yield from request.post()
# 				logging.info('request form: %s'%str(request.__data__))
# 		return (yield from handler(request))
# 	return parse_data

async def  data_factory(app, handler):
	async def parse_data(request):
		if request.method=='POST':
			if request.content_type.startswith('applicaiton/json'):
				request.__data__= await request.json()
				logging.info('request json: %s'%str(request.__data__))
			elif request.content_type.startswith('applicaiton/x-www-form-urlencoded'):
				request.__data__=await request.post()
				logging.info('request form: %s'%str(request.__data__))
		return (await handler(request))
	return parse_data

# response这个middleware用来把返回值转换成web.Response对象再返回，以保证满足aiohttp的要求
# @asyncio.coroutine
# def response_factory(app, handler):
#     def response(request):

async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        # r = yield from handler(request)
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


# def index(request):
# 	# return web.Response(body=b'<h1>Awesome</h1>')
# 	return web.Response(body=b'<h1>Awesome</h1>', headers={'content-type':'text/html'})				#如果body是二进制的时候，要在后面加上content-type为text/html(文本)，不然会变成下载操作。

# @asyncio.coroutine
# def init(loop):
async def init(loop):
	# 连接数据库的时候记得改密码
	# yield from orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password="didn't show for safety reason", db='awesome')
	# yield from orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password="wl9595", db='awesome')
	await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password="wl9595", db='awesome')
	app=web.Application(loop=loop,middlewares=[logger_factory, response_factory])

	# app.router.add_route('GET','/',index)
	init_jinja2(app,filters=dict(datetime=datetime_filter))
	add_routes(app,'handlers')
	add_static(app)
	# srv=yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
	srv=await loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv

loop=asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()


# debug日志：
# ModuleNotFoundError: No module named 'handlers'：
# 必须还要自己再配置一个handlers.py的module，不然会报错。

# OSError: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 9000): 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
# 当程序运行一次后，9000地址就会被占用，直接重复运行会报出以上错误。
# 我的解决方法是在cmd中重置了一下地址，然而这种方法还需要重启电脑，太过麻烦，不知道有没有更好的解决方案。