#-*- coding: UTF-8 -*-

import time
import httpx
from urllib import request

url_list = [
        'http://www.youth.cn/',
        'https://www.baidu.com/img/bd_logo1.png','http://e.firefoxchina.cn/',
        'http://mat1.gtimg.com/www/icon/favicon2.ico',
        'http://www.jd.com/','http://news.ifeng.com/',
        'http://www.suning.com/',
        'http://labs.zol.com.cn/'
        ]

def test_module(module,url,times):
        timelist = []
        for index in range(times):
                try :
                        start = time.clock()
                        obj = module.urlopen(url)
                        timelist.append((time.clock()-start))
                except:
                        continue
                #if isinstance(obj,httpx.ResponseHandler):
                #        print(obj.http_header('statuscode'))
        return timelist

def analyse(timelist):
        totaltime = 0.0
        timelist.sort()
        exclude_max_cnt = int (len(timelist)/50)
        if exclude_max_cnt > 0:
                timelist = timelist[exclude_max_cnt:-exclude_max_cnt]
        for time in timelist:
                totaltime += time
        average = totaltime/len(timelist)
        return [totaltime,average,max(timelist),min(timelist),exclude_max_cnt]

while True :
        times = input('输入请求次数:')
        if not times.isdigit():
                continue
        times = int (times)
        scores = [[],[]]
        for url in url_list:
                print('[+] request %s with %d times,except %d max and min values.'%(url,times,int(times/50)))
                rs = analyse(test_module(httpx,url,times))
                scores[0].append(rs[0])
                print('  ~$> httpx     [total %fs, average %fs, max %fs, min %fs],handle %f requests/s.'%(rs[0],rs[1],rs[2],rs[3],times/rs[0]))
                rs = analyse(test_module(request,url,times))
                scores[1].append(rs[0])
                print('  ~$> urllib    [total:%fs, average:%fs, max:%fs, min:%fs],handle %f requests/s.'%(rs[0],rs[1],rs[2],rs[3],times/rs[0]))

        name_list = ['http','urllib']
        name_index = 0
        for group in scores:
                total_score = 0
                for score in group:
                        total_score += score
                average_score = total_score / len(url_list)
                print('[*] %s  Total time %fs, %fs on each url with %d requests.'%(
                        name_list[name_index],total_score,average_score,times)
                      )
                name_index += 1
