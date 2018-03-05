import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

def index(request):
	# return web.Response(body=b'<h1>Awesome</h1>')
	return web.Response(body=b'<h1>Awesome</h1>', headers={'content-type':'text/html'})				#如果body是二进制的时候，要在后面加上content-type为text/html(文本)，不然会变成下载操作。

@asyncio.coroutine
def init(loop):
	app=web.Application(loop=loop)
	app.router.add_route('GET','/',index)
	srv=yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv

loop=asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()

