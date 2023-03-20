#!/usr/bin/python
# configuration file

import os
# if running on a linux server, uncomment below
# from dotenv import load_dotenv

rand = os.urandom(16)
randa = os.urandom(20)
basedir = os.path.abspath(os.path.dirname(__file__))
# if running on a linux server, uncomment below
# load_dotenv(os.path.join(basedir, '.env'))


# Global configuration syntax
class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or f"{rand}"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://", 1) \
        if os.environ.get("DATABASE_URL") is not None else os.environ.get("DATABASE_URL") or \
                                                       "sqlite:///" + os.path.join(basedir, "bulkops.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_SALT = os.environ.get("SECURITY_SALT") or f"{randa}"

    # mail configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_SUFFIX = os.environ.get("MAIL_SUFFIX")  # e.g example.com
    ADMINS = [os.environ.get("ADMINS")]
    CONTACT_EMAIL = [os.environ.get("CONTACT_EMAIL")]  # delivery address on the contact form

    AUDIT_PER_PAGE = 12
    MESSAGES_PER_PAGE = 8
    LOG_TO_STDOUT = os.environ.get("LOG_TO_STDOUT")
    
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://"

    # App configuration
    APP_NAME = "BulkOps App"
    APP_NAME_SINGLE = "BulkOps"
    APP_ADMIN_USERNAME = "admin"
    # if you do not want users to signup with the below names, you can reserve it by adding it to the list
    APP_RESERVED_KEYWORDS = ["admin", "formeruser", "support", "email", "atlassian"]
    APP_DEFAULT_INSTANCE = "nexusfive.atlassian.net"
    
    # version checker
    APP_VERSION = "v4.1.5\n"
    APP_UPGRADE_URL = "https://github.com/princenyeche/BOP"
    APP_VERSION_URL = "https://raw.githubusercontent.com/princenyeche/BOP/master/VERSION"
    
    # queue time out
    QUEUE_TIMEOUT = os.environ.get("QUEUE_TIMEOUT") or "1h"
    # file size limit
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH") or 2 * 1024 * 1024)
    # support link
    SUPPORT_LINK = os.environ.get("SUPPORT_LINK") or "https://example.com"
    TODAY = os.environ.get("TODAY") or "2021-12-23 15:39:07.437753"
    COOL_DOWN = os.environ.get("COOL_DOWN") or "30m"
    COUNT_DOWN = int(os.environ.get("COUNT_DOWN") or 30)
    # directory storage
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "Files"
