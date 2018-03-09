# 数据访问代码，在数据库中添加数据：
import orm
from models import User, Blog, Comment
import asyncio

# def test():
# 	# yield from orm.create_pool(loop='loop', user='www-data',password='www-data',db='awesome')
# 	yield from orm.create_pool(loop='loop', user='root',password='wl9595',db='awesome')


# 	u=User(name='Test',email='test@example.com',passwd='1234567890',image='about:blank')

# 	yield from u.save()

# for x in test():
# 	pass	

loop = asyncio.get_event_loop()
@asyncio.coroutine
def test():
    #创建连接池,里面的host,port,user,password需要替换为自己数据库的信息。运行的时候记得把密码那里改掉
    yield from orm.create_pool(loop=loop,host='127.0.0.1', port=3306,user='root', password="didn't show for safety reason",db='awesome')
    #没有设置默认值的一个都不能少
    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank',id="123")
    yield from u.save()
    # u.save()

#把协程丢到事件循环中执行
loop.run_until_complete(test())

# debug日志：
# 一开始执行例程，不断显示mysql连接错误(error 2003)，排查了半天连接问题，最后发现例程根本就没写完整。。。下次再出现连接报错要考虑到程序本身是不是有问题
# 后来在执行添加数据的本程序时，25行不断报错。当时以为是yield的问题，于是删掉了yield(见26行)，但是如果没有yield相当于没有return，程序是能跑通，但实际上什么都没有做。
# debug后发现是orm中modelmetaclass遗漏了__fields__的定义，导致属性缺省，一直报错。
# 下次要注意看报错信息。
# 另外今天进一步掌握了mysql的用法，学习了数据表信息查询，删除记录等基本操作。
# 在重复执行该程序第二遍时，因为忘记删除表中的记录，所以不断报"主键重复"的错误，然而我却去把orm的所有子函数用async def的方式重写了一遍orz。。。(又是没看懂报错信息)
# 下次在重复执行插入数据的代码时，记得把上一遍插入的数据删掉。。。或者插入点新数据也行啊hhh
# 今日心得总结：看懂报错信息很重要。。。
# 调代码调的饿死了hhh
# 吃饭去了