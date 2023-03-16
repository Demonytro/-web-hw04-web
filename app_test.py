import json
import socket
import urllib.parse
import pathlib
import mimetypes
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
# from jinja2 import Environment, FileSystemLoader
from datetime import datetime


# env = Environment(loader=FileSystemLoader('.'))
BASE_DIR = pathlib.Path()
BUFFER_SIZE = 2048
PORT_HTTP = 3000
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


class FirstApp(BaseHTTPRequestHandler):
    def do_POST(self):
        logging.info(f'do_POST started')

        length = self.headers.get('Content-Length')
        data = self.rfile.read(int(length))

        logging.info(f'data = {data} ')

        send_data_to_socket(data)
        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        print(route.path)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            # case '/blog':
            #     self.send_html('blog.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file_data:
            self.wfile.write(file_data.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mt = mimetypes.guess_type(filename)
        if mt:
            self.send_header('Content-type', mt[0])
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())



def send_data_to_socket(data):
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
    logging.info(f'data - {data}      after sendto')
    c_socket.close()



def save_data_from_http_server(data):
    parse_data = urllib.parse.unquote_plus(data.decode())
    logging.info(f'parse_data - {parse_data}')
    try:
        # --------- parse from form
        dict_parse = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        # --------- add new key(now)
        add_new_date_key = str(datetime.now())
        new_dict_parse = {add_new_date_key: dict_parse}
        logging.info(f'new_dict_parse - {new_dict_parse}')

        # ----------  read old json

        with open('storage/data.json', 'r', encoding='utf-8') as fd_old:
            dict_parse_old = json.loads(fd_old.read())
            logging.info(f'Read dict_parse_old - {dict_parse_old}')

        # ---------- sum old and new dicts

        sum_dict_parse = dict_parse_old | new_dict_parse
        logging.info(f'sum_dict_parse - {sum_dict_parse}')


        with open('storage/data.json', 'w', encoding='utf-8') as fd:
            json.dump(sum_dict_parse, fd, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.debug(f"for data {parse_data} error: {err}")
    except OSError as err:
        logging.debug(f"Write data {parse_data} error: {err}")


def run_socket_server(host, port):
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_socket.bind((host, port))
    # s_socket.listen()
    logging.info('Socket server started')
    try:
        while True:
            logging.info('in while')
            msg, address = s_socket.recvfrom(BUFFER_SIZE)
            logging.info(f'in while {msg}')
            save_data_from_http_server(msg)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        s_socket.close()


def run_http_server():
    address = ('0.0.0.0', PORT_HTTP)
    httpd = HTTPServer(address, FirstApp)
    logging.info('Http server started')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        httpd.server_close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")

    #  If data/data.json is not exists
    STORAGE_DIR = pathlib.Path().joinpath('storage')
    FILE_STORAGE = STORAGE_DIR / 'data.json'
    if not FILE_STORAGE.exists():
        with open('storage/data.json', 'w', encoding='utf-8') as fd:
            json.dump({}, fd, ensure_ascii=False, indent=4)
    # -------------------

    th_server = Thread(target=run_http_server)
    th_server.start()

    th_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    th_socket.start()
