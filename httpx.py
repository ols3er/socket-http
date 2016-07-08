#-*- coding: UTF-8 -*-

import gzip
import re
import time
import ssl
from socket import AF_INET,SOCK_STREAM,socket,getaddrinfo
from urllib import parse

#import os
#import tempfile
#import threading
#import zlib


__version__ = '2.1.2.2016613'

#-------------------------------------------------------------------------------------#
#                   (C) 2015 by ZhangYiDa <http://www.loogi.cn>                       #
#                              All Rights Reserved.                                   #
#-------------------------------------------------------------------------------------#

from definitions import *



class ResponseHandler:
    def __init__(self,BsConnector = None):
        # event Logger
        self.__recorder = EventRecorder('ResponseHandler')
        
        # arguments for http transporting
        self.__transfer_type_is_set  =  False
        
        self.__transfer_type_is_chunked  =  False
        self.__is_content_encoded_packet  =  False
        self.__buffer  =  EMPTY_BYTES
        self.__content_length  =  -1
        self.__size_recvd   =   0
        
        # http header is a dict
        self.header = {}
        # BaseConnector Object
        self.__connector = BsConnector

    @property
    def data(self):
        return self.__buffer
    def __re_init_response_handler(self,BsConnector):
        if BsConnector :
            self.__connector = BsConnector
        if self.__connector is None:
            return False
        self.__transfer_type_is_set  =  False
        
        self.__transfer_type_is_chunked  =  False
        self.__is_content_encoded_packet  =  False
        self.__buffer  =  EMPTY_BYTES
        self.__content_length  =  -1
        self.__size_recvd   =   0
        
        return True
    
    def Handle(self,BsConnector = None,callback = None):
        ''' callback(totalsize,recvdsize,currentblock)
            [ATTENTION] this callback is only avaliable
            when transporting by Content-Length
        '''
        if not self.__re_init_response_handler(BsConnector):
            return INIT_FAILED
        
        while True or Forever:
            __response_data = self.__connector.recv(RECV_SIZE)

            if not __response_data:
                self.__connector._is_close_for_invoker = True
                return SOCKET_ERROR

            if not self.__transfer_type_is_set:
                __header_end_pos = __response_data.find(RESPONSE_END)

                if __header_end_pos == (-1):
                    self.__recorder.write("Bad response header",
                                          Receive = __response_data)
                    return BAD_HEADER

                self.header = parse_http_response2dict(
                    safe_decoder(__response_data[:__header_end_pos + 4])
                    )
    
                if self.__have_header('Content-Encoding'):
                    self.__is_content_encoded_packet  =  True
                    
                if self.__http_header('Connection').lower() == 'close':
                    self.__connector._is_close_for_invoker = True

                if self.__http_header('Transfer-Encoding').lower() == 'chunked':
                    self.__transfer_type_is_chunked  =   True
                else :
                    if self.__have_header('Content-Length'):
                        self.__content_length = int(
                            self.__http_header('Content-Length')
                            )
                    else :
                        self.__recorder.write(
                            'cannot get data end sign',Receive = __response_data)
                        return False
                __response_data = __response_data[__header_end_pos + 4:]
                self.__transfer_type_is_set = True

            self.__buffer += __response_data

            if self.__transfer_type_is_chunked:
                if __response_data.find(CHUNKED_END) != (-1):
                    break
                
            elif self.__content_length != (-1):
                self.__size_recvd += len(__response_data)
                ''' Invoke the callback funtion '''
                if callback :
                    callback(
                        self.__content_length,
                        self.__size_recvd,
                        __response_data
                        )
                if self.__size_recvd == self.__content_length:
                    break
            else:
                
                self.__recorder.write('发生了未知的错误,退出',headers = self.header)
                return UNKNOWN_ERROR

        if self.__transfer_type_is_chunked:
            __data = self.__process_chunked_blocks(self.__buffer)
            if __data is None:
                return DECODE_ERROR

        if self.__is_content_encoded_packet:
            if self.__http_header('Content-Encoding').lower() == 'gzip':
                content_encode_processor = gzip.decompress
                
            #elif self.__http_header['Content-Encoding'].lower() == 'what':
            #   content_encode_processor = your_routine_name
            else:
                content_encode_processor = self.__default_content_encode_processor
            
            try :
                if self.__transfer_type_is_chunked:
                    self.__buffer = content_encode_processor(__data)
                else:
                    self.__buffer = content_encode_processor(self.__buffer)
                # < all done >
            except Exception as err:
                self.__recorder.write('解码时发生错误,编码格式为 %s'%
                        self.__http_header('Content-Encoding'),Exception = err)
                return DECODE_ERROR
        '''
        # 此部分被注释,
        else:
            # 数据没有进行编码,但是为了安全还是看一下数据是否用CHUNKED传输的(应该是不可能的一步)
            if self.__transfer_type_is_chunked:
                self.__buffer = __data
                # < all done >
        '''
        return True
        
    def __process_chunked_blocks(self,data):
        __cat_buffer = EMPTY_BYTES
        while True or Forever:
            __index = data.find(CRLF)
            if __index != (-1):
                blocksize = int(data[:__index],16)
                if blocksize == 0:
                    break
                __cat_buffer += data[__index + 2:__index + 2 + blocksize]
                data = data[__index + 4 + blocksize:]
            else:
                self.__recorder.write('Error during merge chunked blocks')
                return None
        return __cat_buffer

    def __default_content_encode_processor(data):
        return data
    
    def __http_header(self,key):
        value = self.header.get( key.lower() )
        if not value :
            value = EMPTY_STR
        return value

    def __have_header(self,key):
        return self.__http_header(key)
    
    def http_header(self,key):
        return self.__http_header(key)


class BaseConnector:
    
    def __init__(self,addr = None,ssl = False):
        self.__recorder = EventRecorder('BaseConnector')
        self.__addr         = addr
        self.__connection   = None
        self.__is_ssl       = ssl
        self.__timeout      = HTTP_TIMEOUT
        
        self._is_close_for_invoker = False
        self.__is_addr_reset       = True
        
    @property
    def timeout(self):
        return self.__timeout
    
    @timeout.setter
    def timeout(self,value):
        if not (isinstance(value,int) and \
                    value > 1 and value < 60):
            raise ValueError(
                'timeout is int between 1~60')
        self.__timeout = value
        
    @property
    def socket_instance(self):
        return self.__connection
    
    @socket_instance.setter
    def socket_instance(self,value):
        raise Exception(
            'I takes no Values')
    
    @property
    def use_ssl(self):
        return self.__is_ssl
    
    @use_ssl.setter
    def use_ssl(self,value):
        if not isinstance(value,bool):
            raise TypeError(
                'use_ssl must True OR False')
        self.__is_ssl = value

    def send(self,send_data):
        if self.__is_addr_reset or \
                         self._is_close_for_invoker or \
                                               self.__is_connection_closed():
            self.__connection = socket(AF_INET,SOCK_STREAM)

            if self.__is_ssl:
                self.__connection = ssl.wrap_socket(self.__connection)
                
            try :
                self.__connection.connect(self.__addr)
                
                self.__connection.settimeout(self.__timeout)
                
                self._is_close_for_invoker = False
                self.__is_addr_reset = False
                
            except Exception as exception:
                self.__recorder.write(
                    'Cannot connect %s' % str(self.__addr),
                    Exception = str(exception))
                return None
            
        self.__connection.send(send_data)
        return self

    def __is_connection_closed(self):
        try :
            self.__connection.send(EMPTY_BYTES)
        except :
            return True
        return False
    
    def recv(self,size):
        return self.__connection.recv(size)
    
    def curr_addr(self):
        return self.__addr
    
    def reset_addr(self,addr):
        if not isinstance(addr,tuple):
            raise TypeError(
                'reset_addr need a tuple LIKE ("0.0.0.0",80)')
        self.__is_addr_reset = True
        self.__addr = addr

        

class EventRecorder:
    def __init__(self,module_name):
        self.__module_name = module_name
        
    def write(self,message,**kwargs):
        with open(LOG_FILE,'a+') as streamout:
            strftime = time.strftime('[%F@%T]')
            _string_args = EMPTY_STR
            for key in kwargs:
                _string_args += \
                   (str(key) + ' = ' + str(kwargs[key]) + CRLF_STR)
            log_string = strftime \
                      + CRLF_STR + '  [模块]  ' + self.__module_name \
                      + CRLF_STR + '  [原因]  ' + message \
                      + CRLF_STR + '  [参数]  ' + _string_args
            streamout.write(log_string)



__default_user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"
__base_headers = {
    'Host':None,
    'User-Agent':__default_user_agent,
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding':'gzip, deflate',
    'Connection':'keep-alive'
    }
__base_connector = BaseConnector('0.0.0.0',80)
__response_handler = ResponseHandler()

MAX_REDIRECT_LOOP = 8

def urlopen(url,data_dict = None,
                    custom_header = None,
                            callback = None,
                                     follow_redirect = -1):
    ''' default Method is GET. if data_dict is provided Method will be POST
        custom_header is a dict like {'Accept-Encoding':'what',,,}
        if follow_redirect = 1,urlopen will try to follow the new location
    '''
    if not is_valid_url(url):
        return HTTP_INVALID_URL
    
    __temp_headers = __base_headers.copy()

    if custom_header :
        for key,value in custom_header.items():
            __temp_headers.update({key:value})

    __cur_protocol = get_protocol(url)

    if __cur_protocol == 'http':
        PORT = HTTP_PORT
        __base_connector.use_ssl = False
    else:
        PORT = HTTPS_PORT
        __base_connector.use_ssl = True
    
    new_addr = get_host_addr(get_host_str(url),PORT)
    
    if new_addr != __base_connector.curr_addr():
        __base_connector.reset_addr(new_addr)
    
    __is_post = True if data_dict else False
    if data_dict is not None:
        __post_data = parse.urlencode(data_dict)    
    
    __temp_headers['Host'] = get_host_str(url)
    if __is_post:
        __temp_headers['Content-Length'] = str( len(__post_data) )
        __temp_headers['Content-Type']   = "application/x-www-form-urlencoded"

    __uri = get_request_uri(url)
    if __uri and not __uri.startswith('/'):
        __uri = '/' + __uri
    method_str = '%s %s HTTP/1.1\r\n' % (
            'POST' if __is_post else 'GET',
            __uri if __uri else '/'
            )
    request = method_str + parse_http_req_dict2header(__temp_headers)

    if __is_post:
        request += __post_data

    retval = __response_handler.Handle(
        __base_connector.send(request.encode('utf-8')),callback = callback
        )
    if retval != True:
        return retval

    if __response_handler.http_header('statuscode') in ('301','302','303','307'):
        if follow_redirect != -1 and follow_redirect < MAX_REDIRECT_LOOP:
            __new_url = __response_handler.http_header('location')
            if not __new_url:
                return None
            __cookie = __response_handler.http_header('set-cookie')
            __custom_header = {}
            if __cookie:
                cookie = EMPTY_STR
                for cooki in __cookie:
                    cookie += cooki
                __custom_header.update({"Cookie":cookie})
                
            return urlopen(__new_url,
                           custom_header = __custom_header,
                           callback=callback,
                           follow_redirect = follow_redirect + 1
                           )
    return __response_handler













