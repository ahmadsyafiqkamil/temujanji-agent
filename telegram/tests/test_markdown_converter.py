from telegram.markdown_converter import md_to_html


def test_bold_is_converted():
    assert md_to_html("**Nama** wajib") == "<b>Nama</b> wajib"


def test_inline_code_is_converted():
    assert md_to_html("kode `PSP-001`") == "kode <code>PSP-001</code>"


def test_code_block_is_converted():
    assert md_to_html("```\nabc\n```") == "<pre>abc\n</pre>"


def test_heading_becomes_bold():
    assert md_to_html("### Syarat wajib") == "<b>Syarat wajib</b>"


def test_html_is_escaped():
    assert md_to_html("a < b & c") == "a &lt; b &amp; c"


def test_plain_text_is_unchanged():
    text = "Assalamualaikum, pilih menu."
    assert md_to_html(text) == text
