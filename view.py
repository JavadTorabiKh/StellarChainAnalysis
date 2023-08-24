from flask import Flask, render_template

app = Flask(__name__ ,template_folder='templates')
app.debug = True

@app.route('/')
def index():
    names = ['John', 'Jane', 'Alice', 'Bob']
    return render_template('a.html', names=names)

if __name__ == '__main__':
    app.run()