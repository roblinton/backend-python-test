from alayatodo import app
from alayatodo.sqliteorm import DoesNotExist
from flask import (
    abort,
    flash,
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


@app.route('/todo/<id>/', methods=['GET'])
def todo(id):
    try:
        todo = g.models.todos.get(id=id)
        return render_template('todo.html', todo=todo)
    except DoesNotExist:
        abort(404)


@app.route('/todo/', methods=['GET'])
def todos():
    if not session.get('logged_in'):
        return redirect('/login')
    paging = get_paging(g.models.todos)
    todos = g.models.todos.all()[paging['start'] : paging['end']]
    return render_template('todos.html', todos=todos, paging=paging)


@app.route('/todo/', methods=['POST'])
def todos_POST():
    if not session.get('logged_in'):
        return redirect('/login')
    todo_description = request.form.get('description')
    if not todo_description:
        flash('Description may not be blank.', 'error')
    else:
        g.models.todos.create(user_id=session['user']['id'], description=todo_description)
        g.db.commit()
        page = get_paging(g.models.todos)['max']
        flash('New Todo added.', 'confirmation')
    return redirect('/todo/?p={}'.format(page))


@app.route('/todo/<id>/', methods=['POST'])
def todo_delete(id):
    if not session.get('logged_in'):
        return redirect('/login')
    g.models.todos.where(id=id).delete(id=id)
    g.db.commit()
    paging = get_paging(g.models.todos)
    page = min(paging['start'], paging['max'])
    flash('Todo deleted.', 'confirmation')
    return redirect('/todo/?p={}'.format(page))


def get_paging(model):
    sz = app.config['PER_PAGE']
    tl = model.count()
    mx = tl - (tl%sz or sz)
    try:
        st = min(int(request.args.get('p', 0)), mx)
    except:
        st = 0
    end = min(st+sz, tl)
    return {
        'start': st,
        'end': end,
        'max': mx,
        'limit': sz,
        'total': tl,
        'next': end if st < mx else None,
        'prev': max(0, st-sz) if st > 0 else None,
    }
