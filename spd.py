#!/usr/bin/env python
# coding: utf-8


from wxbot import *
# import wxbot
import redis
import datetime
import requests


redisPool = redis.ConnectionPool(host = '127.0.0.1', port=6379)
r = redis.StrictRedis(connection_pool =redisPool, charset='utf-8')


class MyWXBot(WXBot):

    # def getNickName(self, userId):
    #     for member in self.MemberList:
    #         if userId == member['UserName']:
    #             return member['NickName']
    #     return None

    def handle_msg_all(self, msg):

        if msg['msg_type_id'] == 99 and msg['content']['type'] == 12:
            self.send_msg_by_uid(u"欢迎～由于数据同步存在时间差，请10分钟后分享浦发红包至此账号。以后分享浦发红包至此账号，可以得到最多5个红包回复", msg['user']['id'])

        if msg['msg_type_id'] == 4 and msg['content']['type'] == 99 and msg['content']['data']['tilte'].find(u'抢红包') >= 0:
            self.send_msg_by_uid(u"请勿发送已分享过的红包！打开浦发红包后，请直接分享至此账号！", msg['user']['id'])

        if (msg['msg_type_id'] == 4 or msg['msg_type_id'] == 99)\
                and msg['content']['type'] == 7 \
                and msg['content']['data']['url'].encode('ascii').find('weixin.spdbccc.com.cn') > 0:

            try:
                spUrl = msg['content']['data']['url']
                param = spUrl[spUrl.find('packetId=') + 9: spUrl.find('&amp')]
                wxSpUrl = '''https://open.weixin.qq.com/connect/oauth2/authorize?appid=wxe9d7e3d98ec68189&redirect_uri=https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/StatusDistrubServlet.do?noCheck%3D1%26status%3DJudgeOpenId%26param1%3D''' + str(param).encode("ascii") + '''&response_type=code&scope=snsapi_base&state=STATE&connect_redirect=1#wechat_redirect'''

                # body = {'url': wxSpUrl}
                # res = requests.post('http://suo.im/index.php?m=index&a=urlCreate', data = body).json()
                # tinyUrl = res['list']

                sinaApi = 'http://api.t.sina.com.cn/short_url/shorten.json'
                body = {"source": 1681459862, "url_long": wxSpUrl}
                res = requests.post(sinaApi, data = body).json()[0]
                tinyUrl = res['url_short']

                if not r.exists(tinyUrl):

                    pipe = r.pipeline()
                    pipe.rpush("sphbList", tinyUrl)
                    pipe.hset(tinyUrl, "cnt", 0)
                    pipe.hset(tinyUrl, "from", msg['user']['name'])
                    pipe.hset(tinyUrl, "fromUserId", msg['user']['id'])
                    pipe.execute()

                    # r.lpush("sphbList", tinyUrl)
                    # r.hset(tinyUrl, "cnt", 0)
                    # r.hset(tinyUrl, "from", msg['user']['name'])
                    # r.hset(tinyUrl, "fromUserId", msg['user']['id'])
                    rawResponseUrl = r.lrange("sphbList", 0, 60)
                    responseMsg = u"请勿发送已经共享的链接，否则会被拉黑。红包:"
                    cnt = 0
                    # fromUserName = msg['user']['name']

                    resUrlFromIdSet = set()

                    for url in rawResponseUrl:

                        if int(r.hget(url, 'cnt')) > 4:
                            pipe = r.pipeline()
                            pipe.delete(url)
                            pipe.lrem("sphbList", 0, url)
                            pipe.execute()
                            # r.delete(url)
                            # r.lrem("sphbList", 0, url)
                            continue

                        # and not r.exists(r.hget(url, 'fromUserId').decode('utf-8') + msg['user']['id'])
                        # and not r.exists(r.hget(url, 'fromUserId') + msg['user']['id']) \

                        if r.hget(url, 'fromUserId').decode('utf-8') != msg['user']['id'] \
                                and r.hget(url, 'from').decode('utf-8') != msg['user']['name'] \
                                and not r.exists(r.hget(url, 'fromUserId').decode('utf-8') + msg['user']['id']) \
                                and not r.exists(r.hget(url, 'from').decode('utf-8') + msg['user']['name']) \
                                and not r.exists(msg['user']['id'] + url) \
                                and not r.exists(msg['user']['name'] + url) \
                                and r.hget(url, 'fromUserId').decode('utf-8') not in resUrlFromIdSet \
                                and r.hget(url, 'from').decode('utf-8') not in resUrlFromIdSet \
                                and cnt < 5:

                            resUrlFromIdSet.add(r.hget(url, 'fromUserId').decode('utf-8'))
                            resUrlFromIdSet.add(r.hget(url, 'from').decode('utf-8'))

                            exp = int(datetime.datetime.combine(datetime.date.today(), datetime.time.max).strftime("%s")) - int(time.time())

                            pipe = r.pipeline()
                            pipe.set(r.hget(url, 'fromUserId').decode('utf-8') + msg['user']['id'], 1, ex = exp)
                            pipe.set(r.hget(url, 'from').decode('utf-8') + msg['user']['name'], 1, ex = exp)
                            pipe.set(msg['user']['name'] + url, 1, ex = 648000)
                            pipe.set(msg['user']['id'] + url, 1, ex = 648000)
                            pipe.execute()

                            # r.set(r.hget(url, 'fromUserId').decode('utf-8') + msg['user']['id'], 1, ex = exp)
                            # r.set(r.hget(url, 'fromUserId') + msg['user']['id'], 1, ex = exp)
                            # r.set(msg['user']['id'] + url, 1, ex = 1296000)


                            responseMsg = responseMsg + url + u" from: " + r.hget(url, 'from').decode('utf-8') + u"  "

                            cnt = cnt + 1
                            r.hincrby(url, 'cnt')
                            if int(r.hget(url, 'cnt')) > 4:
                                pipe = r.pipeline()
                                pipe.delete(url)
                                pipe.lrem("sphbList", 0, url)
                                pipe.execute()
                                # r.delete(url)
                                # r.lrem("sphbList", 0, url)
                            if cnt >= 5:
                                break


                    if len(u"请勿发送已经共享的链接，否则会被拉黑。红包:") != len(responseMsg):
                        self.send_msg_by_uid(responseMsg, msg['user']['id'])
                        self.send_msg_by_uid(u' 由于服务器成本，如果好用欢迎发红包打赏分摊服务器费用', msg['user']['id'])
                        self.send_msg_by_uid(u'如发现空链接或以失效链接，请回复：JB+用户名，例如：JB王小二。两次举报会拉黑用户。', msg['user']['id'])
                    if len(u"请勿发送已经共享的链接，否则会被拉黑。红包:") == len(responseMsg):
                        self.send_msg_by_uid("红包库存不足！", msg['user']['id'])

                else:
                    self.send_msg_by_uid(u"重复链接！", msg['user']['id'])

            except Exception,e:
                print Exception,":", e
                self.send_msg_by_uid(u"系统异常！" + str(e), msg['user']['id'])


        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:
            if msg['content']['data'] == u'tsp':
                self.send_msg_by_uid(u'''I am OK''', msg['user']['id'])
            if msg['content']['data'] == u'stsp':
                self.send_msg_by_uid(u'''I am OK''', msg['user']['id'])



            # send_msg_by_uid(u'hi', msg['user']['id'])
            #send_img_msg_by_uid("img/1.png", msg['user']['id'])
            #send_file_msg_by_uid("img/1.png", msg['user']['id'])
'''
    def schedule(self):
        send_msg(u'张三', u'测试')
        time.sleep(1)
'''


def main():
    bot = MyWXBot()
    bot.DEBUG = False
    bot.conf['qr'] = 'png'
    bot.is_big_contact = False   #如果确定通讯录过大，无法获取，可以直接配置，跳过检查。假如不是过大的话，这个方法可能无法获取所有的联系人
    bot.run()
    



if __name__ == '__main__':
    main()
