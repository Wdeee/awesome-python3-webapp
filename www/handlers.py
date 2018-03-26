' url handlers '
import urllib

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
# from apis import Page, APIValueError, APIResourceNotFoundError, APIPermissionError
from apis import Page, APIValueError, APIResourceNotFoundError

from models import User, Comment, Blog, next_id
from config import configs


COOKIE_NAME='awesession'
_COOKIE_KEY=configs.session.secret

# 防止管理员以外的人修改博客：
def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

# 计算页数
def get_page_index(page_str):
	p=1
	try:
		p=int(page_str)
	except ValueError as e:
		pass
	if p<1:
		p=1
	return p

# 计算加密cookie：
def user2cookie(user, max_age):
	# build cookie string by: id-expires-sha1
	expires=str(int(time.time() + max_age))
	s='%s-%s-%s-%s' %(user.id, user.passwd, expires, _COOKIE_KEY)
	L=[user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

# 把博客的文本内容转换成html格式
def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

# 计算解密cookie：
@asyncio.coroutine
def cookie2user(cookie_str):
# async def cookie2user(cookie_str):
	'''
	Parse cookie and load user if cookie is valid.
	'''
	if not cookie_str:
		return None
	try:
		L=cookie_str.split('-')
		if len(L) !=3:
			return None
		uid, expires, sha1=L
		if int(expires)<time.time():
			return None
		user= yield from User.find(uid)
		# user= await User.find(uid)
		if user is None:
			return None
		s='%s-%s-%s-%s' %(uid, user.passwd, expires, _COOKIE_KEY)
		if sha1 !=hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd='wl9595'
		# user.passwd='******'
		return user
	except Exception as e:
		logging.exception(e)
		return None


@get('/')
# async def index(request):
def index(request):

	summary='留白'
	
	# summary1=' 虎扑3月15日讯 洛杉矶湖人队官方今天宣布，他们已经将新秀中锋托马斯-布莱恩特下放至发展联盟。 '
	# summary2=' 虎扑3月14日讯 今日结束的一场常规赛，湖人112-103击败掘金。赛后，湖人前锋凯尔-库兹马在场边接受了采访。 '
	# summary3=' 虎扑3月14日讯 本赛季第三次交手，湖人和掘金之间的对决依然充满了白热化的竞争，这一次，争执双方为湖人前锋朱利叶斯-兰德尔和掘金中锋尼古拉-约基奇。 '
	
	blogs=[
	Blog(id='1',name='Test Blog',summary=summary, created_at=time.time()-120),
	Blog(id='2',name='Something New',summary=summary, created_at=time.time()-3600),
	Blog(id='3',name='Learn Swift',summary=summary, created_at=time.time()-7200)
	
	# 这里的链接(继续阅读)目前还没有搞定
	# Blog(id='1',name='官方：湖人托马斯-布莱恩特下放至发展联盟',summary=summary1, created_at=time.time()-120),
	# Blog(id='2',name='库兹马：是否受伤并不重要，我只想赢球 ',summary=summary2, created_at=time.time()-3600),
	# Blog(id='3',name='兰德尔谈和约基奇冲突：他打算把我手臂搞脱臼 ',summary=summary3, created_at=time.time()-7200)
	]

	return{
	'__template__':'blogs.html',
	'blogs':blogs
	}

# 得到博客中的内容，并转换成html：
@get ('/blog/{id}')
# async def get_blog(id):
def get_blog(id):
	# blog=await Blog.find(id)
	# comments=await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
	blog= yield from Blog.find(id)
	comments= yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
	for c in comments:
		c.html_content=text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)
	return {
	# '__template__': 'blog.html',
	'__template__': 'blogs.html',
	# 这个模板并没有写啊，不知道会不会报错
	'blog':blog,
	'comments': comments
	}


@get('/register')
def register():
	return{
	'__template__':'register.html',
	}

@get('/signin')
def signin():
	return{
	'__template__':'signin.html',
	}


# # 教程的例程写了一个 get_page_index的功能，不过在源代码里又把它删掉了，也没有给出这个函数具体是怎么实现的
# @get('/api/users')
# # def api_get_users(*,page='1'):
# def api_get_users():
# 	# page_index=get_page_index(page)
# 	# num=yield from User.findNumber('count(id')
# 	# p=Page(num,page_index)
# 	# if num==0:
# 	# 	return dict(page=p,users=())
# 	# users=yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
# 	users=yield from User.findAll(orderBy='created_at desc')
# 	for u in users:
# 		u.passwd='wl9595'
# 	# return dict(page=p, users=users)
# 	return dict(users=users)


# 登录API：
@post ('/api/authenticate')
def authenticate(*,email,passwd):
# async def authenticate(*,email,passwd):
	if not email:
		raise APIValueError('email','Invalid email.')
	if not passwd:
		raise APIValueError('passwd','Invalid password.')
	# users=await User.findAll('email=?',[email])
	users= yield from User.findAll('email=?',[email])
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
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400), max_age=86400, httponly=True)
	user.passwd="wl9595"			#记得改
	r.content_type='application/json'
	r.body=json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/signout')
def signout(request):
	referer=request.headers.get('Referer')
	r=web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out.')
	return r

@get('/manage/blogs/create')
def manage_create_blog():
	return{
	'__template__':'manage_blog_edit.html',
	'id':'',
	'action': '/api/blogs'
	}

# 实现用户注册功能：
_RE_EMAIL= re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1= re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
def api_register_user(*,email,name,passwd):
# async def api_register_user(*,email,name,passwd):
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users= yield from User.findAll('email=?', [email])
	# users= await User.findAll('email=?', [email])
	if len(users)>0:
		raise APIError('register:failed','email','Email is already in use.')			#这个逻辑判断没看懂啊
	uid= next_id()
	sha1_passwd= '%s:%s'%(uid,passwd)
	user=User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
	yield from user.save()
	# await user.save()
	# make session cookie:
	r=web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user,86400), max_age=86400, httponly=	True)
	r.set-cookie(COOKIE_NAME, user2cookie(user,86400), max_age=86400, httponly=	True)
	user.passwd='wl9595'
	r.content_type='application/json'
	r.body= json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/api/blogs{id}')
# async def api_get_blog(*, id):
def api_get_blog(*, id):
	# blog=await Blog.find(id)
	blog= yield from Blog.find(id)
	return blog

@post('/api/blogs')
# async def api_create_blog(request, *, name, summary, content):
def api_create_blog(request, *, name, summary, content):
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog= Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
	# await blog.save()
	yield from blog.save()
	return blog