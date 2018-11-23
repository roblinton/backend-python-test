from alayatodo import app
from alayatodo.sqliteorm import DoesNotExist
from flask import (
    abort,
    flash,
    jsonify,
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


@app.route('/todo/<int:id>/', methods=['GET'])
@app.route('/todo/<int:id>/<string:ctype>/', methods=['GET'])
def todo(id, ctype=None):
    try:
        todo = g.models.todos.get(id=id)
        if ctype == 'json':
            return jsonify(todo.todict())
        return render_template('todo.html', todo=todo)
    except DoesNotExist:
        abort(404)


@app.route('/todo/', methods=['GET'])
@app.route('/todo/<string:ctype>/', methods=['GET'])
def todos(ctype=None):
    if not session.get('logged_in'):
        return redirect('/login')
    paging = get_paging(g.models.todos)
    todos = g.models.todos.all()[paging['start'] : paging['end']]
    if ctype == 'json':
        return jsonify({
            'meta': {'offset': paging['start'], 'total': paging['total']},
            'objects': [t.todict() for t in todos],
        })
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


@app.route('/todo/<int:id>/', methods=['POST'])
def todo_post(id):
    action = request.args.get('action', None)
    print('action: {}'.format(action))
    if not session.get('logged_in'):
        return redirect('/login')
    if action == 'delete':
        g.models.todos.where(id=id).delete()
        g.db.commit()
        flash('Todo deleted.', 'confirmation')
    elif action == 'toggle':
        todo = g.models.todos.get(id=id)
        todo.status = 0 if todo.status else 1
        todo.save()
        g.db.commit()
        flash('Set status to: {}'.format('completed' if todo.status else 'pending'), 'confirmation')
    paging = get_paging(g.models.todos)
    page = min(paging['start'], paging['max'])
    return redirect('/todo/?p={}'.format(page))


def get_paging(model):
    try:
        sz = int(request.args.get('l', app.config['PER_PAGE']))
    except:
        sz = app.config['PER_PAGE']
    tl = model.count()
    mx = tl - (tl%sz or sz)
    try:
        st = min(int(request.args.get('p', 0)), tl)
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
