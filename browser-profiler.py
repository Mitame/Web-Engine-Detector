#!/usr/bin/env python2
from flask import Flask, request, Response, render_template
from flask.ext.socketio import SocketIO, emit
from hashlib import md5
from time import time
from binascii import hexlify

from pprint import pprint

# move to the director the file is in.
import os
import sys
os.chdir(os.path.join(*os.path.split(os.path.abspath(sys.argv[0]))[:-1]))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

status_codes = [
    100, 101, 102,
    200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
    300, 301, 302, 303, 304, 305, 306, 307, 308,
    400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 426, 428, 429, 431, 440, 444, 449, 450, 451, 494, 495, 496, 497, 498, 499,
    500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 520, 598, 599
]
test_types = ["js", "iframe"]

tests = []
for test in test_types:
    for code in status_codes:
        tests.append(test + "/" + str(code))

# print(tests)

def md5hash(text):
    return hexlify(md5(text).digest()).decode("utf8")


class Client:

    def __init__(self):
        # make storage lists
        self.requested = {}
        self.sent = []
        self.results = {}
        self.tested_at = time()

        # make uuid
        self.id = md5hash(str(time()).encode("utf8"))

    def get_next_test(self):
        if len(self.sent) == 0:
            testcode = tests[0]
        else:
            testcode = tests[tests.index(self.requested[self.sent[-1]])+1]
        return {"testcode": testcode, "test_id": self.get_test(testcode)}

    def get_test_id(self, test_code):
        return md5hash(str(self.id + test_code).encode("utf8"))

    def get_test(self, test_code):
        test_id = self.get_test_id(test_code)
        self.requested[test_id] = test_code
        return test_id

    def store_sent(self, test_id):
        self.sent.append(test_id)

    def store_result(self, test_id, result):
        self.results[test_id] = result

    def get_results(self):
        ret = {}
        for res in self.results.keys():
            ret[self.requested[res]] = str(self.results[res])
        return ret


clients = {}


@app.route("/")
def main_page():
    if "client_id" in request.cookies and request.cookies["client_id"] in clients:
        client_id = request.cookies["client_id"]
    else:
        x = Client()
        clients[x.id] = x
        client_id = x.id
    return Response(open("static/html/profile.html").read(), 200, headers={"Set-Cookie": "client_id=%s" % client_id})


@app.route('/javascript')
def get_javascript():
    status_code = request.args.get("code")
    test_id = request.args.get("test_id")

    cookies = request.cookies
    client_id = cookies["client_id"]
    client = clients[client_id]

    client.store_sent(test_id)

    payload = """
    console.log("test succeeded");
    passed = true;
    """
    return Response(payload, int(status_code), {"Content-Type": "text/javascript"})

@socketio.on('start_test', namespace="/test")
def on_start_test(data):
    client_id = data["client_id"]
    y = clients[client_id].get_next_test()
    emit("test", y)


@socketio.on('result', namespace="/test")
def on_result_test(data):
    print("got result")
    client_id = data["client_id"]
    test_id = data["test_id"]
    result = bool(int(data["result"]))
    print(data["result"], result)

    clients[client_id].store_result(test_id, result)

    x = clients[client_id].get_next_test()
    if x["testcode"] == "iframe/100":
        pprint(clients[client_id].get_results())
    emit("test", x)



class DetectionClient(Client):

    def __init__(self):
        Client.__init__(self)
        self.renderer = "Unknown"

    def get_next_test(self):
        if len(self.sent) == 0:
            testcode = "js/300"
        else:
            last_test_id = self.sent[-1]
            lasttest = self.requested[last_test_id]
            result = self.results[last_test_id]
            if lasttest == "js/300":
                if result:
                    testcode = "js/205"
                else:
                    self.renderer = "Gecko"
                    return None
            elif lasttest == "js/205":
                if result:
                    testcode = "js/301"
                else:
                    testcode = "js/401"

            elif lasttest == "js/301":
                if result:
                    self.renderer = "Webkit"
                else:
                    self.renderer = "Trident"
                return None

            elif lasttest == "js/401":
                if result:
                    self.renderer = "KHTML"
                else:
                    self.renderer = "Blink"
                return None
            else:
                testcode = None
        return {"testcode": testcode, "test_id": self.get_test(testcode)}

detection_clients = {}

@app.route('/detect')
def detect():
    if "client_id" in request.cookies and request.cookies["client_id"] in detection_clients:
        client_id = request.cookies["client_id"]
    else:
        x = DetectionClient()
        detection_clients[x.id] = x
        client_id = x.id
    return Response(open("static/html/detect.html").read(), 200, headers={"Set-Cookie": "client_id=%s" % client_id})

@app.route('/detect/javascript')
def get_detect_javascript():
    status_code = request.args.get("code")
    test_id = request.args.get("test_id")

    cookies = request.cookies
    client_id = cookies["client_id"]
    client = detection_clients[client_id]

    client.store_sent(test_id)

    payload = """
    console.log("test succeeded");
    passed = true;
    """
    return Response(payload, int(status_code), {"Content-Type": "text/javascript"})



@socketio.on('start_test', namespace="/detect")
def on_start_detect(data):
    print("test")
    client_id = data["client_id"]
    y = detection_clients[client_id].get_next_test()
    print(y)
    emit("test", y)


@socketio.on('result', namespace="/detect")
def on_result_detect(data):
    print("got result")
    client_id = data["client_id"]
    test_id = data["test_id"]
    result = bool(int(data["result"]))
    print(data["result"], result)

    client = detection_clients[client_id]
    print(test_id)
    client.store_result(test_id, result)

    test = client.get_next_test()
    if test is None:
        emit("result", {"renderer": detection_clients[client_id].renderer})
        return
    emit("test", test)


if __name__ == '__main__':
    socketio.run(app, "0.0.0.0", 5000)
