from flask import render_template, request, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
from studentapp import  utils, login, create_app, controllers

app = create_app("default")


if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, port=5000)
