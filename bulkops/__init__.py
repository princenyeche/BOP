import logging
import os
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask
from bulkops.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from redis import Redis
import rq

bulk = Flask(__name__)
bulk.config.from_object(Config)


bulk.config.update(
    SESSION_REFRESH_EACH_REQUEST=True,
    SESSION_COOKIE_NAME="bulkops",
    # add a comment to block the below arguments if running locally
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=None,
)


db = SQLAlchemy(bulk)
migrate = Migrate(bulk, db)
login = LoginManager(bulk)
login.login_view = "signin"
mail = Mail(bulk)
moment = Moment(bulk)

basedir = os.path.abspath(os.path.dirname(__file__))
LOG_FOLDER = "Logs"
bulk.config["LOG_FOLDER"] = os.path.join(basedir, LOG_FOLDER)
our_logs = os.path.join(bulk.config["LOG_FOLDER"])

bulk.redis = Redis.from_url(bulk.config["REDIS_URL"])
bulk.job_queue = rq.Queue("bulkops-jobs", connection=bulk.redis)

# log notification configuration
if not bulk.debug:
    if bulk.config["MAIL_SERVER"]:
        auth = None
        if bulk.config["MAIL_USERNAME"] or bulk.config["MAIL_PASSWORD"]:
            auth = (bulk.config["MAIL_USERNAME"], bulk.config["MAIL_PASSWORD"])
        secure = None
        if bulk.config["MAIL_USE_TLS"]:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(bulk.config["MAIL_SERVER"], bulk.config["MAIL_PORT"]),
            fromaddr="no-reply@" + bulk.config["MAIL_SUFFIX"],
            toaddrs=bulk.config["ADMINS"], subject="BulkOps App Failure",
            credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        bulk.logger.addHandler(mail_handler)
    if bulk.config['LOG_TO_STDOUT']:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        bulk.logger.addHandler(stream_handler)
    else:
        # error logging configurations
        if not os.path.exists(our_logs):
            os.mkdir(our_logs)
        file_handler = RotatingFileHandler(os.path.join(our_logs, "bulkops.log"), maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"))
        file_handler.setLevel(logging.INFO)
        bulk.logger.addHandler(file_handler)

        bulk.logger.setLevel(logging.INFO)
        bulk.logger.info("BulkOps Start")


db.init_app(bulk)
migrate.init_app(bulk, db)
login.init_app(bulk)
mail.init_app(bulk)
moment.init_app(bulk)

from bulkops import database
from bulkops.main import views
from bulkops.secure import views
from bulkops.errors import errors

# end of program
