from flask import Flask, render_template, request, redirect, url_for
import app.conectToNeo4j as con

app = Flask(__name__, template_folder='templates')
# app.debug = True


@app.route('/')
def index():
    return render_template('form.html')


@app.route('/process', methods=['POST'])
def process_form():
    account, amount = con.getData(request.form['pub1'], request.form['pub2'])
    print(account)
    return redirect(url_for('result', names=account))


@app.route('/result')
def result():
    names = request.args.getlist('names')
    return render_template('view.html', names=names)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
