from flask import render_template
from flask_wtf.csrf import CSRFError
from bulkops import db, bulk
from bulkops.database import Messages


@bulk.errorhandler(404)
def not_found_error(error):
    return render_template("error/404.html", title="404 Error: Not Found", Messages=Messages), 404


@bulk.errorhandler(405)
def method_not_allowed(error):
    return render_template("error/405.html", title="405 Error: Method not Allowed", Messages=Messages), 405


@bulk.errorhandler(413)
def request_not_allowed(error):
    return render_template("error/413.html", title="413 Error: Request not Allowed", Messages=Messages), 413


@bulk.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    support = bulk.config["SUPPORT_LINK"]
    return render_template("error/500.html", title="500 Error: Internal Server Error", 
                           Messages=Messages, support=support), 500


@bulk.errorhandler(503)
def service_unavailable(error):
    return render_template("error/503.html", title="503 Error: Service Unavailable", Messages=Messages), 503


@bulk.errorhandler(CSRFError)
def handle_csrf_error(error):
    return render_template("error/400.html", reason=error.description, Messages=Messages), 400
