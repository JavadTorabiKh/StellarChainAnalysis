from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__ ,template_folder='templates')
app.debug = True

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/process', methods=['POST'])
def process_form():
    names = [request.form['pub1'], request.form['pub2']]
    return redirect(url_for('result', names=names))

@app.route('/result')
def result():
    names = request.args.getlist('names')
    return render_template('view.html', names=names)

if __name__ == '__main__':
    app.run()
