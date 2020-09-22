#!/usr/bin/python
# configuration file

import os
# if running on a linux server, uncomment below
# from dotenv import load_dotenv

rand = os.urandom(16)
basedir = os.path.abspath(os.path.dirname(__file__))
# if running on a linux server, uncomment below
# load_dotenv(os.path.join(basedir, '.env'))


# Global configuration syntax
class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or f"{rand}"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
                              "sqlite:///" + os.path.join(basedir, "bulkops.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # mail configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_SUFFIX = os.environ.get("MAIL_SUFFIX")  # e.g example.com
    ADMINS = ["no-reply@example.com"]
    CONTACT_EMAIL = ["admin@example.com"]  # delivery address on the contact form

    AUDIT_PER_PAGE = 12
    MESSAGES_PER_PAGE = 8
    LOG_TO_STDOUT = os.environ.get("LOG_TO_STDOUT")

    # App configuration
    APP_NAME = "BulkOps App"
    APP_NAME_SINGLE = "BulkOps"
    APP_ADMIN_USERNAME = "admin"
    # if you do not want users to signup with the below names, you can reserve it by adding it to the list
    APP_RESERVED_KEYWORDS = ["admin", "formeruser", "support", "email", "atlassian"]
    APP_DEFAULT_INSTANCE = "nexusfive.atlassian.net"
    
    # version checker
    APP_VERSION = f"v1.2.2\n"
    APP_UPGRADE_URL = f"https://github.com/princenyeche/BOP"
    APP_VERSION_URL = f"https://raw.githubusercontent.com/princenyeche/BOP/master/version.txt"
