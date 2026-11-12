"""APP FACTORY — create_app(config_name). JWT chính, session fallback /admin."""
from flask import Flask, jsonify

from config import config_by_name
from studentapp.extensions import db, migrate, login, csrf, jwt
from studentapp.exceptions import AppError


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    from studentapp import models  # noqa: F401
    from studentapp.controllers import ALL_BLUEPRINTS

    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
        csrf.exempt(bp)

    from studentapp.controllers.admin_controller import init_admin

    init_admin(app)

    from studentapp.repositories import user_repository

    @login.user_loader
    def load_user(user_id):
        return user_repository.get_by_id(user_id)

    @jwt.user_lookup_loader
    def jwt_lookup(_jwt_header, jwt_data):
        return user_repository.get_by_id(jwt_data.get("sub"))

    @login.unauthorized_handler
    def unauthorized():
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": "Phiên làm việc đã hết hạn hoặc Token không hợp lệ. Vui lòng đăng nhập lại!",
        }), 401

    @jwt.unauthorized_loader
    def jwt_missing(reason):
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": "Phiên làm việc đã hết hạn hoặc Token không hợp lệ. Vui lòng đăng nhập lại!",
        }), 401

    @jwt.invalid_token_loader
    def jwt_invalid(reason):
        return jsonify({"error": "UNAUTHORIZED", "message": "Token không hợp lệ hoặc đã hết hạn."}), 401

    @jwt.expired_token_loader
    def jwt_expired(_h, _d):
        return jsonify({"error": "UNAUTHORIZED", "message": "Token không hợp lệ hoặc đã hết hạn."}), 401

    @app.errorhandler(AppError)
    def handle_app_error(e):
        return jsonify({"error": e.error, "message": e.message}), e.status_code

    @app.errorhandler(404)
    def nf(e):
        return jsonify({"error": "NOT_FOUND", "message": "Không tìm thấy API."}), 404

    @app.errorhandler(405)
    def mm(e):
        return jsonify({"error": "BAD_REQUEST", "message": "Sai method."}), 405

    return app
