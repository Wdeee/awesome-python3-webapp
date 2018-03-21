' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from aiohttp import web

from coroweb import get, post
from apis import APIValueError, APIResourceNotFoundError, APIError

from models import User, Comment, Blog, next_id
from config import configs


COOKIE_NAME='awesession'
_COOKIE_KEY=configs.session.secret


# 计算加密cookie：
def user2cookie(user, max_age):
	# build cookie string by: id-expires-sha1
	expires=str(int(time.time()+max_age))
	s='%s-%s-%s-%s' %(user.id, user.passwd, expires, _COOKIE_KEY)
	L=[user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)


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

@get('/register')
def register():
	return{
	'__template__':'register.html',
	}


# 教程的例程写了一个 get_page_index的功能，不过在源代码里又把它删掉了，也没有给出这个函数具体是怎么实现的
@get('/api/users')
# def api_get_users(*,page='1'):
def api_get_users():
	# page_index=get_page_index(page)
	# num=yield from User.findNumber('count(id')
	# p=Page(num,page_index)
	# if num==0:
	# 	return dict(page=p,users=())
	# users=yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	users=yield from User.findAll(orderBy='created_at desc')
	for u in users:
		u.passwd='wl9595'
	# return dict(page=p, users=users)
	return dict(users=users)

# 登录API：
@post ('/api/authenticate')
def authenticate(*,email,passwd):
	if not email:
		raise APIValueError('email','Invalid email.')
	if not passwd:
		raise APIValueError('passwd','Invalid password.')
	users=yield from User.findAll('email=?',[email])
	if len(users)==0:
		raise APIValueError('email','Email not exist.')
	user=users[0]
	# check password:
	sha1=hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd','Invalid password.')
	# authenticate OK, set cookie:
	r=web.Response()
	r=set_cookie(COOKIE_NAME,user2cookie(user,86400), max_age=86400, httponly=True)
	user.passwd="didn't show for safety reason"			#记得改
	r.content_type='application/json'
	r.body=json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r



# 实现用户注册功能：

_RE_EMAIL= re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1= re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
def api_register_user(*,email,name,passwd):
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users= yield from User.findAll('email=?', [email])
	if len(users)>0:
		raise APIError('register:failed','email','Email is already in use.')			#这个逻辑判断没看懂啊
	uid= next_id()
	sha1_passwd= '%s:%s'%(uid,passwd)
	user=User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
	yield from user.save()
	# make session cookie:
	r=web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user,86400), max_age=86400, httponly=	True)
	user.passwd='wl9595'
	r.content_type='application/json'
	r.body= json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r