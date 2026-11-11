from flask import render_template, request, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
from studentapp import app, dao, utils, login


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET'])
def login_view():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_process():
    username = request.form.get('username')
    password = request.form.get('password')

    u = dao.authenticate(username=username, password=password)
    if u:
        login_user(user=u)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('login.html', err_msg='Invalid username or password!')


@app.route('/register', methods=['GET'])
def register_view():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register_process():
    password = request.form.get('password')
    confirm = request.form.get('confirm')  # Make sure your register.html uses name="confirm" for password confirmation

    err_msg = None
    if not password or not confirm or password != confirm:
        err_msg = 'Passwords do not match!'
    else:
        try:

            data = request.form.copy()
            if 'confirm' in data:
                del data['confirm']


            dao.create_user(**data)
            return redirect(url_for('login_view'))
        except Exception as ex:
            err_msg = f'System Error: {str(ex)}'

    return render_template('register.html', err_msg=err_msg)

@app.route('/logout')
@login_required
def logout_process():
    logout_user()
    return redirect(url_for('login_view'))


@login.user_loader
def get_user(user_id):
    return dao.get_user_by_id(user_id)


if __name__ == '__main__':
    with app.app_context():
        from studentapp import admin
        app.run(debug=True)
