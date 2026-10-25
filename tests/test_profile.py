import io

from expense_tracker.profile import PHOTO_MAX_BYTES, detect_image_type

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
JPEG = b"\xff\xd8\xff" + b"0" * 100


def save_details(client, **fields):
    data = {"full_name": "", "email": "", "phone": "", "address": "", **fields}
    return client.post("/profile", data=data, follow_redirects=True)


def upload(client, content, filename="photo.png"):
    return client.post(
        "/profile/photo/upload",
        data={"photo": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_profile_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_photo_requires_login(client):
    assert client.get("/profile/photo").status_code == 302


def test_save_details_and_show_them_again(user):
    client = user()
    response = save_details(
        client,
        full_name="Alice Example",
        email="alice@example.com",
        phone="+1 (555) 010-2030",
        address="12 Market Street\nSample City",
    )

    assert b"Profile saved." in response.data
    page = client.get("/profile").data
    assert b'value="Alice Example"' in page
    assert b'value="alice@example.com"' in page
    assert b'value="+1 (555) 010-2030"' in page
    assert b"12 Market Street" in page


def test_details_are_optional(user):
    client = user()
    response = save_details(client)
    assert b"Profile saved." in response.data


def test_invalid_email_is_rejected_and_not_saved(user):
    client = user()
    response = save_details(client, full_name="Alice", email="not-an-email")

    assert b"Email must be a valid address" in response.data
    assert b"Profile saved." not in response.data
    # The typed values come back so the user can fix them.
    assert b'value="not-an-email"' in response.data


def test_phone_needs_seven_digits(user):
    client = user()
    response = save_details(client, phone="12-34")
    assert b"Phone must have at least 7 digits" in response.data


def test_phone_rejects_letters(user):
    client = user()
    response = save_details(client, phone="555-CALL-NOW")
    assert b"Phone must have at least 7 digits" in response.data


def test_name_and_address_length_limits(user):
    client = user()
    assert b"Name must be 100 characters or fewer" in save_details(client, full_name="x" * 101).data
    assert b"Address must be 300 characters or fewer" in save_details(client, address="x" * 301).data


def test_upload_png_is_stored_and_served(user):
    client = user()
    response = upload(client, PNG)

    assert b"Profile photo updated." in response.data
    served = client.get("/profile/photo")
    assert served.status_code == 200
    assert served.mimetype == "image/png"
    assert served.data == PNG
    assert served.headers["Cache-Control"] == "private, no-cache"


def test_header_shows_uploaded_photo(user):
    client = user()
    upload(client, JPEG, filename="me.jpg")

    page = client.get("/").data
    assert b'class="avatar-link"' in page
    assert b'<img class="avatar" src="/profile/photo"' in page


def test_header_shows_initial_without_photo(user):
    client = user("alice")
    page = client.get("/").data
    assert b'class="avatar avatar-initial"' in page
    assert b'>A</span>' in page


def test_initial_comes_from_full_name_when_set(user):
    client = user("alice")
    save_details(client, full_name="bob smith")
    assert b'>B</span>' in client.get("/").data


def test_logout_sits_under_avatar(user):
    client = user("alice")
    page = client.get("/").data

    account = page.index(b'class="account"')
    logout = page.index(b'action="/auth/logout"')
    assert account < logout < page.index(b"</header>")

    assert b"Signed in as" not in page


def test_no_avatar_when_logged_out(client):
    page = client.get("/").data
    assert b"avatar-link" not in page


def test_non_image_is_rejected_even_with_image_name(user):
    client = user()
    response = upload(client, b"<html>not an image</html>", filename="evil.png")

    assert b"Photo must be a JPEG, PNG, GIF or WebP image." in response.data
    assert client.get("/profile/photo").status_code == 404


def test_svg_is_rejected(user):
    client = user()
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    response = upload(client, svg, filename="icon.svg")
    assert b"Photo must be a JPEG, PNG, GIF or WebP image." in response.data


def test_photo_just_over_two_megabytes_is_rejected_by_route(user):
    client = user()
    response = upload(client, PNG + b"0" * PHOTO_MAX_BYTES)
    assert b"Photo must be 2 MB or smaller." in response.data


def test_photo_far_over_limit_gets_too_large_page(user):
    client = user()
    response = upload(client, PNG + b"0" * (PHOTO_MAX_BYTES * 2))
    assert response.status_code == 413
    assert b"That upload is too large" in response.data


def test_other_forms_keep_the_small_body_limit(user):
    client = user()
    response = client.post("/expenses", data={"description": "x" * 20_000})
    assert response.status_code == 413


def test_remove_photo_restores_initial(user):
    client = user("alice")
    upload(client, PNG)

    response = client.post("/profile/photo/remove", follow_redirects=True)

    assert b"Profile photo removed." in response.data
    assert client.get("/profile/photo").status_code == 404
    assert b'class="avatar avatar-initial"' in client.get("/").data


def test_photos_are_private_to_each_user(user):
    alice = user("alice")
    upload(alice, PNG)

    bob = user("bob")
    assert bob.get("/profile/photo").status_code == 404


def test_detect_image_type():
    assert detect_image_type(JPEG) == "image/jpeg"
    assert detect_image_type(PNG) == "image/png"
    assert detect_image_type(b"GIF89a" + b"0" * 10) == "image/gif"
    assert detect_image_type(b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 10) == "image/webp"
    assert detect_image_type(b"RIFF\x00\x00\x00\x00WAVE" + b"0" * 10) is None
    assert detect_image_type(b"hello") is None
