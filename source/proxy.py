#!/bin/sh -
# coding=gbk

"exec" "python" "-O" "$0" "$@"

__doc__ = """
TmsProxy
Write By Tinymins
At 2013-6-11 21:40:01
For Network Project
Website: ZhaiYiMing.CoM
How to use?
look at the demo ini file.
all config is inside that file.
"""

__version__ = "1.0.1"

import BaseHTTPServer, select, socket, SocketServer, urlparse, threading, re, os, time, datetime, sys, hashlib#, base64
# shared lock: define outside threading class
lock = threading.RLock()


class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    __base = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle = __base.handle

    server_version = "Tinymins Proxy/" + __version__
    rbufsize = 0                        # self.rfile Be unbuffered
    
    s_filters = []

    def handle(self):
        (ip, port) =  self.client_address
        if hasattr(self, 'allowed_clients') and ip not in self.allowed_clients:
            self.raw_requestline = self.rfile.readline()
            if self.parse_request(): self.send_error(403)
        else:
            self.__base_handle()
    
    def _send_connect_error(self,msg=""):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>朽Ӊ����~</title></head>")
        self.wfile.write("<body><p>Sorry...</p>")
        self.wfile.write("<p>��ء�朽��ƺ��ĵ��˰�_(:�١���)_ %s</p><p>%s</p>" % (self.path, msg) )
        self.wfile.write("</body></html>")
        
    def _send_access_denied(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>���C����~</title></head>")
        self.wfile.write("<body><p>Sorry...</p>")
        self.wfile.write("<p>��������~���L���ă��ݱ����C����߹_(:�١���)_ %s</p>" % self.path)
        self.wfile.write("</body></html>")

    def _get_http_status(self, s_http_context):
        s_http_context = s_http_context[0:s_http_context.find("\r")]
        s_http_context = s_http_context.split(" ")
        if s_http_context[1]:
            try:
                return int(s_http_context[1])
            except ValueError:
                return False
        return False

    def _get_http_header(self, s_http_context, s_find_header):
        s_find_header = s_find_header+": "
        iFindPos = s_http_context.find(s_find_header)
        iHeaderLen = s_http_context.find("\r\n\r\n")
        if iFindPos>-1 and iFindPos<iHeaderLen:
            s_http_context=s_http_context[iFindPos+len(s_find_header):]
            s_http_context=s_http_context[:s_http_context.find("\r")]
        else:
            s_http_context=False
        return s_http_context

    def _get_http_header_length(self, s_http_context):
        iHeaderLen = s_http_context.find("\r\n\r\n")
        if iHeaderLen<0: iHeaderLen=0
        else: iHeaderLen+=4
        return iHeaderLen

    def _get_http_timestamp(self, s_http_context):
        LastModifyGMT = self._get_http_header(s_http_context, "Last-Modified")
        if LastModifyGMT:
            return int(time.mktime(time.strptime(LastModifyGMT, '%a, %d %b %Y %H:%M:%S GMT')))
        else:
            return 0
    
    def _connect_to(self, netloc, soc):
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i+1:])
        else:
            host_port = netloc, 80
        with lock: print "- Connecting to %s:%d" % host_port
        try: soc.connect(host_port)
        except socket.error, arg:
            try: msg = arg[1]
            except: msg = arg
            #self.send_error(404, msg)
            # �B�ӷ�����ʧ��
            with lock: print "- �B�Ӊĵ���_(:�١���)_[",self.path,"]"
            self._send_connect_error(msg)
            return 0
        return 1

    def do_CONNECT(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(self.path, soc):
                with lock:
                    print "- ",
                    self.log_request(200)
                self.wfile.write(self.protocol_version +
                                 " 200 Connection established\r\n")
                self.wfile.write("Proxy-Agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")
                self._read_write(soc, 300)
        finally:
            with lock: print "- Socket In Closed!"
            soc.close()
            self.connection.close()

    def do_GET(self):
        (scheme, host, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')
        if not host:
        #if scheme != 'http' or fragment or not host:
            self.send_error(400, "Bad URL %s" % self.path)
            return
        # filter URL as re
        for s_filter in self.s_filters:
            if re.search(s_filter[0], scheme, re.IGNORECASE):
                if re.search(s_filter[1], host, re.IGNORECASE):
                    if re.search(s_filter[2], path, re.IGNORECASE):
                        if re.search(s_filter[3], query, re.IGNORECASE):
                            self._send_access_denied()
                            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(host, soc):
                # �B�ӷ������ɹ�
                with lock:
                    print "- ",
                    self.log_request("","")
                soc.send( "%s %s %s\r\n" % (
                    self.command,
                    urlparse.urlunparse(('', '', path, params, query, '')),
                    self.request_version))
                self.headers['Connection'] = 'close'
                del self.headers['Proxy-Connection']
                for key_val in self.headers.items():
                    soc.send("%s: %s\r\n" % key_val)
                soc.send("\r\n")
                self._read_write(soc)
        finally:
            with lock: print "- Socket Out Closed!"
            soc.close()
            self.connection.close()

    def _cache_read_write(self, s_data, i, out):
        # ����������200 OK �t������
        if self._get_http_status(s_data)!=200: return False
        # �@ȡ��ǰ�������ĕr�g��
        sever_timestamp = self._get_http_timestamp(s_data)
        # ��ǰ������û�������޸ĕr�g �t���؟o����
        if not sever_timestamp: return False
        # ��ǰ�������������޸ĕr�g �t�ڴűP�ό����Ƿ��о���
        (scheme, host, path, params, query, fragment) = urlparse.urlparse(self.path, 'http')
        if not os.path.exists('cache'): os.mkdir('cache')
        if not os.path.exists('cache/' + host): os.mkdir('cache/' + host)
        s_cache_path = "cache/" + host + "/" + hashlib.md5(path).hexdigest() #base64.b64encode(path)

        #########
        # �Lԇ�xȡ����
        if os.path.exists(s_cache_path):
            # ������� �t���_�����ļ��@ȡ���������޸ĕr�g
            with open(s_cache_path,'rb') as f:
                s_cache_data = f.read(4096)
                cache_timestamp = self._get_http_timestamp(s_cache_data)
                cache_size = (str(os.path.getsize(s_cache_path)-self._get_http_header_length(s_cache_data))).strip(' \t\n\r')
                org_size = self._get_http_header(s_cache_data, "Content-Length")
                if org_size: org_size = org_size.strip(' \t\n\r')
                # �Дྏ���ǲ������µģ���С춮�ǰ�������r�g���� and �����Ƿ���������С���Header������
                if cache_timestamp and cache_timestamp>=sever_timestamp and cache_size==org_size:
                    out.send(s_cache_data)
                    package_index=0
                    while True:
                        s_cache_data = f.read(8192)
                        if s_cache_data:
                            out.send(s_cache_data)
                            with lock: print "- cache loading [len=%s] package-index:%s" % (len(s_cache_data), package_index)
                            package_index+=1
                        else:
                            break
                    with lock: print "- cache loaded: " + s_cache_path
                    return True
        #########      
        # �ܵ��@�e �f�����治���ڻ��߲������� ���߾��治����
        # �h����ǰ����
        if os.path.exists(s_cache_path): os.remove(s_cache_path)   

        # �xȡ�����K�Ҵ��뾏��
        with open(s_cache_path,'wb') as f: #open requested file
            f.write(s_data)
            out.send(s_data)
            package_index=0
            while True:
                data = i.recv(8192)
                if data:
                    f.write(data)
                    out.send(data)
                    with lock: print "- cache saving [len=%s] package-index:%s" % (len(data), package_index)
                    package_index+=1
                else:
                    break
        with lock: print "- cache saved: " + s_cache_path
        return True
    
    def _read_write(self, soc, max_idling=20):
        iw = [self.connection, soc]
        ow = []
        count = 0
        package_index = 0
        while 1:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 3)
            if exs: break
            if ins:
                for i in ins:
                    if i is soc:
                        out = self.connection
                    else:
                        out = soc
                    data = i.recv(8192)
                    #dl = len(data)
                    if data:
                        # �Д��ǲ���HTTP�^
                        if cmp(data[0:4],"HTTP")==0:
                            with lock: print "- Got HTTP Data [" + data[0:data.find("\r")] + "] package-index:" + str(package_index)
                            #os.system('title "[' + data[0:data.find("\r")] + '] ' + self.path + '"'[0:255])
                            # �Д�ԓHTTP���Ƿ��������޸ĕr�g��ӛ
                            if self._get_http_timestamp(data):
                                # �� �t�Lԇ�xȡ/���뾏��
                                if self._cache_read_write(data,i,out):
                                    # ����/�xȡ�ɹ� �tֱ�ӷ���
                                    return
                        else:
                            # ��������r�� �����D�l
                            with lock: print "- Got Data [len=" + str(len(data)) + "] package-index:" + str(package_index)
                        out.send(data)
                        package_index+=1
                        count = 0
            else:
                with lock: print "- idle " + str(count)
            if count == max_idling: break

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET

class ThreadingHTTPServer (SocketServer.ThreadingMixIn,
                           BaseHTTPServer.HTTPServer): pass

if __name__ == '__main__':
    from sys import argv
    os.system('title "Python��������� - Group&421"')
    if not argv[1:]:
        # default port
        argv.append("3280")
    if argv[1:] and argv[1] in ('-h', '--help'):
        # �@ʾ������Ϣ
        with lock: print argv[0], "[port [allowed_client_name ...]]"
    else:
        # �_���������
        if argv[2:]:
            # �O�ô������ClientIP�����Σ������Y��Ĳ��o����գ�
            allowed = []
            for name in argv[2:]:
                client = socket.gethostbyname(name)
                allowed.append(client)
                with lock: print "Accept: %s (%s)" % (client, name)
            ProxyHandler.allowed_clients = allowed
            del argv[2:]
        else:
            # ����IP���o�����
            with lock: print "Any clients will be served..."
        if os.path.exists('proxy.ini'):
            # ���dURL�^�V���t���_ʽ
            with lock: print "- Loading Blocked Regular Expressions:"
            ins = open( "proxy.ini", "r" )
            for line in ins:
                line = line.strip()
                nPos = line.find("#")
                if nPos>=0:
                    line = line[0:nPos]
                    line = line.strip()
                if len(line)==0: continue
                s_filter = line.split(" ")
                if len(s_filter)<4:
                    with lock:
                        print "  - Proxy.ini Format Error At Line ",len(s_filters),":",line
                        #print "Program Exited!"
                    #exit(1)
                    continue
                if cmp(s_filter[0][0],":")==0:
                    s_filter[0] = s_filter[0][1:]
                else:
                    s_filter[0] = re.escape(s_filter[0]).replace("\\*",".*")
                    s_filter[1] = re.escape(s_filter[1]).replace("\\*",".*")
                    s_filter[2] = re.escape(s_filter[2]).replace("\\*",".*")
                    s_filter[3] = re.escape(s_filter[3]).replace("\\*",".*")
                with lock: print "  - ",s_filter[0],s_filter[1],s_filter[2],s_filter[3]
                ProxyHandler.s_filters.append([s_filter[0],s_filter[1],s_filter[2],s_filter[3]])
            with lock: print "Get Proxy Local IP:", socket.gethostbyname(socket.gethostname()) #�õ�����ip            
        BaseHTTPServer.test(ProxyHandler, ThreadingHTTPServer)
