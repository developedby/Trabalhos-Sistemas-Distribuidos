import flask

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels.</p>"

@app.route('/create', methods=['POST'])
def read_post():
    card = flask.request.get_json()   
    print(card)
    # novo_limite = card.get("limit") - card.get("transaction").get("amount")
    response = {"aprovado":True,"novoLimite":10}
    return flask.jsonify(response)

@app.route('/delete', methods=['DELETE'])
def delete_post():
    card = flask.request.get_json()   
    print(card)
    # novo_limite = card.get("limit") - card.get("transaction").get("amount")
    response = {"deletado":True}
    return flask.jsonify(response)

@app.route('/update', methods=['PUT'])
def update_post():
    card = flask.request.get_json()   
    print(card)
    # novo_limite = card.get("limit") - card.get("transaction").get("amount")
    response = {"atualizado":True}
    return flask.jsonify(response)

app.run(port=4444)