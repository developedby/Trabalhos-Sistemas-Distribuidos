import time

import flask


app = flask.Flask(__name__)
count = 0

@app.route('/')
def index():
    def stream():
        global count
        while True:
            yield 'data: count={}\n\n'.format(count)
            print(f'yielding {count}')
            count += 1
            time.sleep(3)

    # Fica mandando stream das notificações enquanto status do cliente for connected
    response = flask.Response(stream(), mimetype='text/event-stream')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response