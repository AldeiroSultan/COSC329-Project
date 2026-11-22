"""Static checks for the dashboard front end (web/). There is no JavaScript test runner,
so these guard the usual breakages: a script pointing at an element or icon that does not
exist, emoji instead of icons, a theme losing contrast, or a guided example drifting from
the planner's real behaviour."""

import re

import pytest
from fastapi.testclient import TestClient

from study_planner import config as cfg
from study_planner.api import app
from study_planner.scenarios import SCENARIOS

WEB = cfg.ROOT / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "styles.css").read_text(encoding="utf-8")
APP_JS = (WEB / "app.js").read_text(encoding="utf-8")
TOUR_JS = (WEB / "tour.js").read_text(encoding="utf-8")

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕⌚-⏿️]")
HTML_IDS = set(re.findall(r'\bid="([\w-]+)"', HTML))


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_page_and_scripts_are_served(client):
    for path in ["/", "/styles.css", "/app.js", "/tour.js"]:
        assert client.get(path).status_code == 200, path
    assert "javascript" in client.get("/tour.js").headers["content-type"]  # needed for ES modules
    assert "./tour.js" in APP_JS


def test_every_element_the_script_looks_up_exists():
    looked_up = set(re.findall(r"\$\('([\w-]+)'\)", APP_JS)) | set(re.findall(r"getElementById\('([\w-]+)'\)", APP_JS))
    assert looked_up, "expected the script to look up elements"
    assert looked_up <= HTML_IDS, sorted(looked_up - HTML_IDS)


def test_tour_targets_and_navigation_point_at_real_elements():
    targets = set(re.findall(r"target: '#([\w-]+)'", APP_JS))
    nav = set(re.findall(r'href="#([\w-]+)"', HTML))
    sections = set(re.findall(r"data-section=\"([\w-]+)\"", HTML))
    spy = set(re.findall(r"'([\w-]+)'", re.search(r"const SECTIONS = \[(.*?)\]", APP_JS).group(1)))
    assert len(targets) >= 10
    assert targets <= HTML_IDS | {"rail"}, sorted(targets - HTML_IDS)
    assert nav <= HTML_IDS, sorted(nav - HTML_IDS)
    assert sections == spy


def test_every_icon_used_exists_in_the_sprite():
    sprite = set(re.findall(r'<symbol id="i-([\w-]+)"', HTML))
    used = set(re.findall(r'href="#i-([\w-]+)"', HTML)) | set(re.findall(r"#i-([\w-]+)", APP_JS))
    for call in re.findall(r"icon\(([^)]*)\)", TOUR_JS):
        used |= set(re.findall(r"'([\w-]+)'", call))
    assert {"sun", "moon", "help"} <= used
    assert used <= sprite, sorted(used - sprite)


@pytest.mark.parametrize("name,text", [("index.html", HTML), ("styles.css", CSS), ("app.js", APP_JS), ("tour.js", TOUR_JS)])
def test_no_emoji_anywhere(name, text):
    assert EMOJI.findall(text) == [], name


def hex_tokens(selector):
    block = re.search(re.escape(selector) + r"\s*\{(.*?)\}", CSS, re.S).group(1)
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\b", block))


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


THEMES = {"light": ':root,\n:root[data-theme="light"]', "dark": ':root[data-theme="dark"]'}


@pytest.mark.parametrize("theme", THEMES)
def test_both_themes_meet_wcag_aa_contrast(theme):
    tokens = hex_tokens(THEMES[theme])
    pairs = [("text", "bg"), ("muted", "bg"), ("muted", "well"), ("accent", "bg"), ("danger", "bg"),
             ("on-accent", "accent-a"), ("on-accent", "accent-b")]
    for foreground, background in pairs:
        assert contrast(tokens[foreground], tokens[background]) >= 4.5, (theme, foreground, background)


def test_themes_define_the_same_tokens():
    assert set(hex_tokens(THEMES["light"])) == set(hex_tokens(THEMES["dark"]))


def test_theme_is_applied_before_first_paint_and_toggle_is_a_switch():
    script = HTML.index("localStorage.getItem('theme')")
    assert script < HTML.index('rel="stylesheet"')
    assert 'id="theme-toggle"' in HTML and 'role="switch"' in HTML and 'aria-checked="false"' in HTML
    assert "prefers-color-scheme: dark" in HTML


def test_help_menu_is_wired_up_accessibly():
    assert 'aria-haspopup="menu"' in HTML and 'aria-controls="help-menu"' in HTML and 'role="menu"' in HTML
    assert 'role="dialog"' in TOUR_JS or "'role', 'dialog'" in TOUR_JS


def test_three_guided_examples_match_real_scenarios():
    guided = re.findall(r"\{ name: '([\w]+)', takeaway", APP_JS)
    assert guided == ["struggling", "advanced", "one_weak_spot"]
    expected = {s.name: s.expected_action for s in SCENARIOS}
    # the takeaway texts describe these outcomes
    assert [expected[name] for name in guided] == ["intense", "rest", "focused"]
    labels = set(re.findall(r"^\s+(\w+): '[^']+',$", re.search(r"const PROFILE_LABEL = \{(.*?)\n\};", APP_JS, re.S).group(0), re.M))
    assert {s.name for s in SCENARIOS} <= labels


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion: reduce" in CSS
    assert "reducedMotion" in TOUR_JS
