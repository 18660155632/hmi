import pyDes
import binascii

# pyDes.des（key，[mode]，[IV]，[pad]，[padmode]）
# 加密密钥的字节、加密类型、可选参数用来设置填充字符、设置填充模式

key = "Hdys123."

def jiami(text):
    iv = secret_key = key
    k = pyDes.des(secret_key, pyDes.CBC, iv, pad=None, padmode = pyDes.PAD_PKCS5)
    data = k.encrypt(text, padmode=pyDes.PAD_PKCS5)
    return binascii.b2a_hex(data).decode()

def jiemi(text):
    iv = secret_key = key
    k = pyDes.des(secret_key, pyDes.CBC, iv, pad=None, padmode = pyDes.PAD_PKCS5)
    data = k.decrypt(binascii.a2b_hex(text), padmode=pyDes.PAD_PKCS5)
    return data.decode()

'''
while True:
    x = input("请输入明文：\n")
    xx = jiami(x.strip())
    xxx = jiemi(xx.strip())
    print(xx)
    print(xxx)
'''