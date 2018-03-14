' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id

@get('/')
async def index(request):
	# users= await User.findAll()
	# summary='Lorem ipsum dolor sit amet, consectrtur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	summary1=' 虎扑3月15日讯 洛杉矶湖人队官方今天宣布，他们已经将新秀中锋托马斯-布莱恩特下放至发展联盟。 '
	summary2=' 虎扑3月14日讯 今日结束的一场常规赛，湖人112-103击败掘金。赛后，湖人前锋凯尔-库兹马在场边接受了采访。 '
	summary3=' 虎扑3月14日讯 本赛季第三次交手，湖人和掘金之间的对决依然充满了白热化的竞争，这一次，争执双方为湖人前锋朱利叶斯-兰德尔和掘金中锋尼古拉-约基奇。 '
	blogs=[
	# Blog(id='1',name='Test Blog',summary=summary, created_at=time.time()-120),
	# Blog(id='2',name='Something New',summary=summary, created_at=time.time()-3600),
	# Blog(id='3',name='Learn Swift',summary=summary, created_at=time.time()-7200)
	# 这里的链接(继续阅读)目前还没有搞定
	Blog(id='1',name='官方：湖人托马斯-布莱恩特下放至发展联盟',summary=summary1, created_at=time.time()-120),
	Blog(id='2',name='库兹马：是否受伤并不重要，我只想赢球 ',summary=summary2, created_at=time.time()-3600),
	Blog(id='3',name='兰德尔谈和约基奇冲突：他打算把我手臂搞脱臼 ',summary=summary3, created_at=time.time()-7200)
	]
	return{
	'__template__':'blogs.html',
	'blogs':blogs
	}