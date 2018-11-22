from alayatodo import app
from alayatodo.sqliteorm import DoesNotExist
from flask import (
    abort,
    g,
    redirect,
    render_template,
    request,
    session
    )


@app.route('/')
def home():
    with app.open_resource('../README.md', mode='rb') as f:
        readme = "".join(l.decode('utf-8') for l in f)
        return render_template('index.html', readme=readme)


@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_POST():
    username = request.form.get('username')
    password = request.form.get('password')
    try:
        user = g.models.users.get(username=username, password=password)
        if user:
            session['user'] = dict(user.items())
            session['logged_in'] = True
            return redirect('/todo')
    except DoesNotExist:
        pass
    return redirect('/login')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user', None)
    return redirect('/')


@app.route('/todo/<id>', methods=['GET'])
def todo(id):
    try:
        todo = g.models.todos.get(id=id)
        return render_template('todo.html', todo=todo)
    except DoesNotExist:
        abort(404)


@app.route('/todo', methods=['GET'])
@app.route('/todo/', methods=['GET'])
def todos():
    if not session.get('logged_in'):
        return redirect('/login')
    todos = g.models.todos.list()
    return render_template('todos.html', todos=todos)


@app.route('/todo', methods=['POST'])
@app.route('/todo/', methods=['POST'])
def todos_POST():
    if not session.get('logged_in'):
        return redirect('/login')
    g.models.todos.create(user_id=session['user']['id'], description=request.form.get('description', ''))
    g.db.commit()
    return redirect('/todo')


@app.route('/todo/<id>', methods=['POST'])
def todo_delete(id):
    if not session.get('logged_in'):
        return redirect('/login')
    g.db.models.todos.delete(id=id)
    g.db.commit()
    return redirect('/todo')
