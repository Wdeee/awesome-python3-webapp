import config_default


# 重写属性设置，获取方法
# 支持通过属性名访问键值对的值，属性名将被当做键名
class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self,names=(),values=(),**kw):
    	# super().__init__(**kw)				#下面那句的super函数是python2的定义方式，真正使用的时候不一定跑得通，如果不行就用这句
    	super(Dict,self).__init__(**kw)			#在这里，dict是父类，Dict是子类，这一句是在Dict这个子类里补充定义了__init__方法，目的是为了支持x.y的dict形式。补充的内容是9，10两行代码
    	for k,v in zip(names,values):			#zip函数是"打包"函数，相当于是把names和values里面的内容重新提取并打包成(names1,values1),(names2,values2)...
    		self[k]=v

    def __getattr__(self,key):
    	try:
    		return self[key]
    	except KeyError:
    		raise AttributeError(r"'Dict' object has no attribute '%s'"%key)

    def __setattr__(self,key,value):
    	self[key]=value

def merge(defaults,override):
	r={}
	for k,v in defaults.items():
		if k in override:
			if isinstance(v,dict):
				r[k]=merge(v,override[k])
			else:
				r[k]=override[k]
		else:
			r[k]=v
	return r

# 把从经过merge函数处理复写后的dict对象configs转变为文件中从dict基类派生出的Dict类对象，从而实现xxx.key的取值功能。
def toDict(d):
	# pass
	D=Dict()
	for k,v in d.items():
		D[k]=toDict(v) if isinstance(v,dict) else v 			#如果值是一个dict递归将其转换为Dict再赋值，否则直接赋值
	return D

configs=config_default.configs

try:
	import config_override
	configs=merge(configs,config_override.configs)
except ImportError:
	pass

configs = toDict(configs)