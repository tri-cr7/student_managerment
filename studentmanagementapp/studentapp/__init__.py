import os

from flask import Flask, jsonify, request, send_from_directory

from config import config_by_name
from studentapp.extensions import db, migrate, login, csrf, jwt
from studentapp.exceptions import AppError

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)

def create_app(config_name="default"):

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    from studentapp import models
    from studentapp.controllers import ALL_BLUEPRINTS

    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
        csrf.exempt(bp)

    from studentapp.controllers.admin_controller import init_admin

    init_admin(app)

    init_cors(app)
    init_frontend(app)

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

def init_cors(app):

    allowed = app.config.get(
        "CORS_ORIGINS",
        os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500,"
            "http://localhost:3000,http://127.0.0.1:3000,"
            "http://localhost:5173,http://127.0.0.1:5173",
        ),
    )
    if isinstance(allowed, str):
        allowed = [o.strip() for o in allowed.split(",") if o.strip()]

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and (origin in allowed or "*" in allowed):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With, Accept"
        )
        response.headers["Access-Control-Max-Age"] = "600"
        return response

    @app.route("/<path:_any>", methods=["OPTIONS"])
    def cors_preflight(_any):
        return ("", 204)

def init_frontend(app):

    if not os.path.isdir(FRONTEND_DIR):
        return

    @app.get("/")
    def index():
        return send_from_directory(os.path.join(FRONTEND_DIR, "pages"), "index.html")

    @app.get("/<path:filename>")
    def static_files(filename):

        pages_dir = os.path.join(FRONTEND_DIR, "pages")
        if os.path.isfile(os.path.join(pages_dir, filename)):
            return send_from_directory(pages_dir, filename)

        if os.path.isfile(os.path.join(FRONTEND_DIR, filename)):
            resp = send_from_directory(FRONTEND_DIR, filename)

            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp
        return jsonify({"error": "NOT_FOUND", "message": "Không tìm thấy."}), 404
