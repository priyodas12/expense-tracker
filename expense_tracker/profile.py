from flask import Blueprint, Response, abort, flash, g, redirect, render_template, request, url_for

from expense_tracker.auth import login_required
from expense_tracker.db import get_db
from expense_tracker.validation import validate_profile

bp = Blueprint("profile", __name__)

PHOTO_MAX_BYTES = 2 * 1024 * 1024
# Room for the multipart envelope around the file, so a photo just under the limit still fits.
PHOTO_UPLOAD_LIMIT = PHOTO_MAX_BYTES + 64 * 1024

EMPTY_DETAILS = {"full_name": "", "email": "", "phone": "", "address": ""}


def detect_image_type(data):
    """Return the MIME type for a supported image, judged by its file signature.

    The uploaded filename and browser-supplied type are ignored, so only real
    JPEG, PNG, GIF and WebP files are stored and served."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def avatar_context():
    """What the header avatar needs: whether a photo exists, and an initial to show without one."""
    user = g.get("user")
    if user is None:
        return None

    row = get_db().execute(
        "SELECT full_name, photo_type FROM profiles WHERE user_id = ?", (user["id"],)
    ).fetchone()
    name = (row["full_name"] if row and row["full_name"] else user["username"]).strip()
    return {
        "has_photo": bool(row and row["photo_type"]),
        "initial": name[:1].upper(),
    }


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def index():
    db = get_db()
    details = dict(EMPTY_DETAILS)
    row = db.execute("SELECT * FROM profiles WHERE user_id = ?", (g.user["id"],)).fetchone()
    if row:
        details.update({key: row[key] for key in EMPTY_DETAILS})
    has_photo = bool(row and row["photo_type"])

    if request.method == "POST":
        data, errors = validate_profile(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            # Show what was typed, so the user can correct it rather than retype.
            details = {key: request.form.get(key, "").strip() for key in EMPTY_DETAILS}
        else:
            db.execute(
                """
                INSERT INTO profiles (user_id, full_name, email, phone, address)
                VALUES (:user_id, :full_name, :email, :phone, :address)
                ON CONFLICT (user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    email = excluded.email,
                    phone = excluded.phone,
                    address = excluded.address
                """,
                {**data, "user_id": g.user["id"]},
            )
            db.commit()
            flash("Profile saved.", "success")
            return redirect(url_for("profile.index"))

    return render_template("profile.html", details=details, has_photo=has_photo)


@bp.route("/profile/photo")
@login_required
def photo():
    row = get_db().execute(
        "SELECT photo, photo_type FROM profiles WHERE user_id = ?", (g.user["id"],)
    ).fetchone()
    if row is None or row["photo"] is None:
        abort(404)

    response = Response(row["photo"], mimetype=row["photo_type"])
    # Each user's photo is private and can change, so let the browser revalidate it.
    response.headers["Cache-Control"] = "private, no-cache"
    return response


@bp.route("/profile/photo/upload", methods=["POST"])
@login_required
def upload_photo():
    file = request.files.get("photo")
    if file is None or not file.filename:
        flash("Choose an image to upload.", "error")
        return redirect(url_for("profile.index"))

    data = file.read(PHOTO_MAX_BYTES + 1)
    if len(data) > PHOTO_MAX_BYTES:
        flash("Photo must be 2 MB or smaller.", "error")
        return redirect(url_for("profile.index"))

    photo_type = detect_image_type(data)
    if photo_type is None:
        flash("Photo must be a JPEG, PNG, GIF or WebP image.", "error")
        return redirect(url_for("profile.index"))

    db = get_db()
    db.execute(
        """
        INSERT INTO profiles (user_id, photo, photo_type) VALUES (?, ?, ?)
        ON CONFLICT (user_id) DO UPDATE SET photo = excluded.photo, photo_type = excluded.photo_type
        """,
        (g.user["id"], data, photo_type),
    )
    db.commit()
    flash("Profile photo updated.", "success")
    return redirect(url_for("profile.index"))


@bp.route("/profile/photo/remove", methods=["POST"])
@login_required
def remove_photo():
    db = get_db()
    db.execute("UPDATE profiles SET photo = NULL, photo_type = NULL WHERE user_id = ?", (g.user["id"],))
    db.commit()
    flash("Profile photo removed.", "success")
    return redirect(url_for("profile.index"))
