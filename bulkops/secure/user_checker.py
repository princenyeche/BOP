from flask_login import current_user
from flask import redirect, url_for, flash
from functools import wraps


def validate_account(control):
    @wraps(control)
    def allow_accounts(*args, **kwargs):
        if current_user.confirm_user is False or current_user.confirm_user is None:
            flash("Please verify your account!", "alert-warning")
            return redirect(url_for("unconfirmed"))
        return control(*args, **kwargs)

    return allow_accounts
