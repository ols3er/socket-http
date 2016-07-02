#-*- coding: UTF-8 -*-


import time
import re
from socket import getaddrinfo

#-------------------------------------------------------------------------------------#
#                   (C) 2015 by ZhangYiDa <http://www.loogi.cn>                       #
#                              All Rights Reserved.                                   #
#-------------------------------------------------------------------------------------#


# definitions
HTTP_PORT         =   (80)
HTTPS_PORT        =   (443)
HTTP_TIMEOUT      =   (60)
RECV_SIZE         =   (10485760)

#HTTP_INIT         =   (0,'HTTP_INIT')
#HTTP_OK           =   (1,'HTTP_OK')
#HTTP_ERROR        =   (2,'HTTP_ERROR')
#HTTP_START        =   (3,'HTTP_START')
#HTTP_CANT_CONNECT =   (4,'HTTP_CANT_CONNECT')

HTTP_INVALID_URL  =   (5,'INVALID_URL')
INIT_FAILED       =   (0,'INIT_FAILED')
SOCKET_ERROR      =   (1,'SOCKET ERROR')
BAD_HEADER        =   (3,'BAD HEADER')
UNKNOWN_ERROR     =   (4,'UNKNOWN ERROR')
DECODE_ERROR      =   (5,'DECODE ERROR')
ENCODE_ERROR      =   (6,'ENCODE ERROR')

EMPTY_BYTES       =   b''
EMPTY_STR         =   ''
Forever           =   True                   # ^_^ ,this is not important
RESPONSE_END      =   b'\x0d\x0a\x0d\x0a'       # http/s respond end sign
CHUNKED_END       =   b'\x30\x0d\x0a\x0d\x0a'   # transfer-encoding:chunked end sign
CRLF              =   b'\x0d\x0a'               # CRLF \x0d\x0a
CRLF_STR          =   '\x0d\x0a'             # CRLF / str
SPACE             =   b'\x20'                 # SPACE ' '
SPACE_STR         =   '\x20'
LOG_FILE          =   'httx.log'     # error log file


_rex_ALL_url = re.compile(r'https?://([\w\.-]+\w+)(:\d+)?(.+)?')
_rex_http_status_line = re.compile(r'HTTP/(...) (...)')
_rex_header_kv = re.compile('([\w-]+): (.+)')

__charsets = ['utf-8','gbk','ascii','ISO-8859-1']

def safe_decoder(data):
    for charset in __charsets:
        try :
            return data.decode(charset)
        except UnicodeDecodeError:
            continue
    return EMPTY_STR

def safe_encoder(data):
    for charset in __charsets:
        try :
            return data.encode(charset)
        except UnicodeEncodeError:
            continue
    return EMPTY_BYTES


def get_host_addr(host,port): return getaddrinfo(host,port)[0][4]

def is_valid_url(url): return _rex_ALL_url.match(url)

def get_request_uri(url): return _rex_ALL_url.match(url).groups()[2]

def get_host_str(url): return _rex_ALL_url.match(url).groups()[0]

def get_protocol(url): return url.split(':')[0].lower()

def assume_port(url): return _rex_ALL_url.match(url).groups()[1]

def parse_http_response2dict(header_str):
    __hdr_dict = {}

    __match = _rex_http_status_line.match(header_str)
    if not __match:
        return {}
    
    __match = __match . groups()
    __hdr_dict . update({'version':__match[0]})
    __hdr_dict . update({'status':__match[1]})

    for line in header_str.splitlines():
        __match = _rex_header_kv.match(line)
        if __match :
            __match = __match . groups()
            key , value = __match[0].lower(),__match[1]
            if __hdr_dict.get(key) :
                if not isinstance(__hdr_dict[key],list):
                    __hdr_dict[key] = [__hdr_dict[key]]
                __hdr_dict[key].append(value)
                continue
            __hdr_dict.update({key:value})
    return __hdr_dict

def parse_http_req_dict2header(req_dict):
    req_header = EMPTY_STR
    for key,value in req_dict.items():
        req_header += (key + ': ' + value + CRLF_STR)
    return req_header + CRLF_STR




