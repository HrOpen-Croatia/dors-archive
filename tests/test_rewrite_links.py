"""Tests for scripts/rewrite_links.py.

The rewriter converts absolute dorscluc.org URLs in crawled HTML into
archive-relative paths, per the path-based archive layout:
    https://www.dorscluc.org/foo         -> /main/foo
    https://2013.dorscluc.org/foo        -> /2013/foo
    https://files.dorscluc.org/foo       -> /main/files/foo   (fallback)
    https://2013.dorscluc.org/files/x    -> /2013/files/x

External URLs, relative URLs, mailto/tel/anchor-only URLs are untouched.
"""
from scripts.rewrite_links import rewrite_html


def test_absolute_www_href_becomes_main_path():
    html = '<a href="https://www.dorscluc.org/past-conferences/">past</a>'
    assert rewrite_html(html) == (
        '<a href="/main/past-conferences/">past</a>'
    )


def test_absolute_bare_root_becomes_main_root():
    html = '<a href="https://dorscluc.org/">root</a>'
    assert rewrite_html(html) == '<a href="/main/">root</a>'


def test_year_subdomain_href_becomes_year_path():
    html = '<a href="https://2013.dorscluc.org/speakers/">s</a>'
    assert rewrite_html(html) == '<a href="/2013/speakers/">s</a>'


def test_year_subdomain_with_http_scheme():
    html = '<a href="http://2014.dorscluc.org/">2014</a>'
    assert rewrite_html(html) == '<a href="/2014/">2014</a>'


def test_img_src_rewritten():
    html = '<img src="https://2015.dorscluc.org/wp-content/uploads/logo.png">'
    assert rewrite_html(html) == (
        '<img src="/2015/wp-content/uploads/logo.png">'
    )


def test_srcset_all_urls_rewritten():
    html = (
        '<img srcset="https://2016.dorscluc.org/a.png 1x, '
        'https://2016.dorscluc.org/b.png 2x">'
    )
    assert rewrite_html(html) == (
        '<img srcset="/2016/a.png 1x, /2016/b.png 2x">'
    )


def test_external_url_untouched():
    html = '<a href="https://example.com/">ext</a>'
    assert rewrite_html(html) == html


def test_relative_url_untouched():
    html = '<a href="/about/">a</a><img src="foo.png">'
    assert rewrite_html(html) == html


def test_mailto_untouched():
    html = '<a href="mailto:info@dorscluc.org">mail</a>'
    assert rewrite_html(html) == html


def test_fragment_only_untouched():
    html = '<a href="#top">top</a>'
    assert rewrite_html(html) == html


def test_query_string_preserved():
    html = (
        '<a href="https://2018.dorscluc.org/?page_id=42&lang=hr">p</a>'
    )
    assert rewrite_html(html) == (
        '<a href="/2018/?page_id=42&lang=hr">p</a>'
    )


def test_files_subdomain_goes_to_main_files():
    html = '<a href="https://files.dorscluc.org/media/x.pdf">pdf</a>'
    assert rewrite_html(html) == (
        '<a href="/main/files/media/x.pdf">pdf</a>'
    )


def test_inline_style_url_rewritten():
    html = (
        '<div style="background: url(https://2019.dorscluc.org/bg.jpg);">'
        'x</div>'
    )
    assert rewrite_html(html) == (
        '<div style="background: url(/2019/bg.jpg);">x</div>'
    )


def test_meta_refresh_content_rewritten():
    html = (
        '<meta http-equiv="refresh" '
        'content="5;url=https://2020.dorscluc.org/">'
    )
    assert rewrite_html(html) == (
        '<meta http-equiv="refresh" content="5;url=/2020/">'
    )


def test_form_action_rewritten():
    html = '<form action="https://www.dorscluc.org/search"></form>'
    assert rewrite_html(html) == '<form action="/main/search"></form>'


def test_no_change_returns_identical_string():
    html = '<p>no urls here</p>'
    assert rewrite_html(html) == html


def test_json_escaped_url_in_inline_script_rewritten():
    html = r'{"root":"https:\/\/www.dorscluc.org\/wp-json\/"}'
    assert rewrite_html(html) == r'{"root":"\/main\/wp-json\/"}'


def test_json_escaped_year_subdomain_rewritten():
    html = r'"ji":"https:\/\/2026.dorscluc.org\/wp-includes\/foo.js?ver=6.1.1"'
    assert rewrite_html(html) == (
        r'"ji":"\/2026\/wp-includes\/foo.js?ver=6.1.1"'
    )


def test_url_encoded_in_query_rewritten():
    html = (
        '<link href="https://example.com/oembed?url='
        'https%3A%2F%2F2026.dorscluc.org%2Fperson%2Fnoah%2F">'
    )
    assert rewrite_html(html) == (
        '<link href="https://example.com/oembed?url='
        '%2F2026%2Fperson%2Fnoah%2F">'
    )


def test_url_encoded_www_rewritten():
    html = 'url=https%3A%2F%2Fwww.dorscluc.org%2Fpast-conferences%2F'
    assert rewrite_html(html) == 'url=%2Fmain%2Fpast-conferences%2F'
