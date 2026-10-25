from datetime import date


def test_footer_links_on_homepage(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'<footer class="site-footer">' in response.data
    assert b'href="/terms-and-conditions"' in response.data
    assert b'href="/privacy-policy"' in response.data


def test_footer_copyright_uses_current_year(client):
    response = client.get("/")
    expected = f"&copy; {date.today().year} Penny Trail. All rights reserved.".encode()
    assert expected in response.data


def test_terms_page_renders(client):
    response = client.get("/terms-and-conditions")
    assert response.status_code == 200
    assert b"<h2>Terms &amp; Conditions</h2>" in response.data
    assert b"Effective date: 25 October 2026" in response.data
    assert b"Limitation of liability" in response.data


def test_privacy_page_renders(client):
    response = client.get("/privacy-policy")
    assert response.status_code == 200
    assert b"<h2>Privacy Policy</h2>" in response.data
    assert b"Google Fonts" in response.data
    assert b"Your rights" in response.data


def test_policy_pages_have_no_placeholders(client):
    for path in ("/terms-and-conditions", "/privacy-policy"):
        assert b"PLACEHOLDER" not in client.get(path).data


def test_footer_present_on_auth_pages(client):
    response = client.get("/auth/login")
    assert b'<footer class="site-footer">' in response.data
