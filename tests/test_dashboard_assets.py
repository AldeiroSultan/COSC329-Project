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


def test_browsers_must_revalidate_the_page_and_its_assets(client):
    """Regression: without this a browser kept an old stylesheet and script and mixed them with the new page."""
    for path in ["/", "/styles.css", "/app.js", "/tour.js"]:
        assert client.get(path).headers["cache-control"] == "no-cache", path
    assert client.get("/api/scenarios").headers.get("cache-control") != "no-cache"


def test_asset_urls_carry_the_same_version():
    css = re.search(r'href="/styles\.css\?v=(\d+)"', HTML)
    script = re.search(r'src="/app\.js\?v=(\d+)"', HTML)
    tour = re.search(r"from '\./tour\.js\?v=(\d+)'", APP_JS)
    assert css and script and tour
    assert css.group(1) == script.group(1) == tour.group(1)


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
    pairs = [("text", "bg"), ("muted", "bg"), ("muted", "well"), ("accent", "bg"), ("accent", "well"), ("danger", "bg"),
             ("on-accent", "accent-a"), ("on-accent", "accent-b"),
             ("hero-text", "hero-a"), ("hero-text", "hero-b"), ("hero-muted", "hero-a"), ("hero-muted", "hero-b")]
    for foreground, background in pairs:
        assert contrast(tokens[foreground], tokens[background]) >= 4.5, (theme, foreground, background)


def test_themes_define_the_same_tokens():
    assert set(hex_tokens(THEMES["light"])) == set(hex_tokens(THEMES["dark"]))


def test_theme_is_applied_before_first_paint_and_toggle_is_a_switch():
    script = HTML.index("localStorage.getItem('theme')")
    assert script < HTML.index('rel="stylesheet"')
    assert 'id="theme-toggle"' in HTML and 'role="switch"' in HTML and 'aria-checked="false"' in HTML
    assert "prefers-color-scheme: dark" in HTML


def test_all_text_is_set_in_lexend_deca_and_no_serif_remains():
    stack = re.search(r"--font:\s*([^;]+);", CSS).group(1)
    assert stack.startswith('"Lexend Deca"')
    assert re.findall(r"font-family:\s*([^;]+);", CSS) == ["var(--font)", "var(--font)"]  # body and the network labels
    assert not re.search(r"Georgia|Palatino|Times|Iowan|(?<!sans-)serif\b", CSS)
    assert "family=Lexend+Deca" in HTML and "display=swap" in HTML
    assert HTML.count('rel="preconnect"') == 2


def test_font_failure_falls_back_to_system_fonts():
    stack = re.search(r"--font:\s*([^;]+);", CSS).group(1)
    assert "system-ui" in stack and stack.rstrip().endswith("sans-serif")


def test_help_menu_is_wired_up_accessibly():
    assert 'aria-haspopup="menu"' in HTML and 'aria-controls="help-menu"' in HTML and 'role="menu"' in HTML
    assert 'role="dialog"' in TOUR_JS or "'role', 'dialog'" in TOUR_JS


def test_three_guided_examples_match_real_scenarios():
    block = re.search(r"const GUIDED = \[(.*?)\];", APP_JS).group(1)
    guided = re.findall(r"'(\w+)'", block)
    assert guided == ["struggling", "advanced", "one_weak_spot"]
    expected = {s.name: s.expected_action for s in SCENARIOS}
    # together the three examples show three different outcomes
    assert [expected[name] for name in guided] == ["intense", "rest", "focused"]
    profiles = re.search(r"const PROFILE_LABEL = \{(.*?)\n\};", APP_JS, re.S).group(1)
    assert {s.name for s in SCENARIOS} <= set(re.findall(r"^\s+(\w+): '", profiles, re.M))


def test_every_action_has_a_recommendation_line_and_a_plain_meaning():
    """The guide's summary starts with a recommendation and explains the score in words."""
    keys = {action.key for action in cfg.ACTIONS}
    for table in ("ACTION_ICON", "ACTION_LEAD", "ACTION_MEANING", "ACTION_NAME", "ACTION_PHRASE"):
        body = re.search(rf"const {table} = \{{(.*?)\n\}};", APP_JS, re.S).group(1)
        assert set(re.findall(r"^\s+(intense|focused|light|rest):", body, re.M)) == keys, table


def test_guide_text_is_connected_prose_not_a_list_of_fragments():
    for phrase in ("Because of that", "which means", "That said", "so the model"):
        assert phrase in APP_JS, phrase
    assert "tour-rows" not in CSS and "rows" not in TOUR_JS


def test_tour_buttons_fit_inside_the_card():
    """Regression: Back, Replay and Done together were wider than the card, so Done stuck out."""
    card = re.search(r"\.tour-card \{[^}]*?width: (\d+)px;[^}]*?padding: (\d+)px (\d+)px", CSS, re.S)
    width, pad_x = int(card.group(1)), int(card.group(3))
    minimum = int(re.search(r"\.tour-actions \.btn \{[^}]*?min-width: (\d+)px", CSS).group(1))
    gap = int(re.search(r"\.tour-actions \{[^}]*?gap: (\d+)px", CSS).group(1))
    assert 3 * minimum + 2 * gap <= width - 2 * pad_x
    assert "flex-wrap: wrap" in re.search(r"\.tour-actions \{[^}]*\}", CSS).group(0)


def test_theme_switch_animates_and_respects_reduced_motion():
    assert "startViewTransition" in APP_JS and "theme-fade" in APP_JS
    assert "reducedMotion() || !document.startViewTransition" in APP_JS  # the wipe is skipped, the fade is not
    assert "::view-transition-new(root)" in CSS and ".theme-fade" in CSS
    knob = re.search(r"\.switch-knob \{[^}]*\}", CSS).group(0)
    assert "transition: transform" in knob
    assert re.search(r"\.switch-knob \.icon \{[^}]*transition:", CSS)
    reduced = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
    assert ".switch-knob { transition: transform" in reduced  # the switch still slides when motion is reduced


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion: reduce" in CSS
    assert "reducedMotion" in TOUR_JS


def test_action_icons_exist_in_the_sprite():
    sprite = set(re.findall(r'<symbol id="i-([\w-]+)"', HTML))
    icons = re.search(r"const ACTION_ICON = \{(.*?)\n\};", APP_JS, re.S).group(1)
    assert set(re.findall(r": '([\w-]+)'", icons)) <= sprite


def test_summary_is_a_wide_two_column_card_that_stacks_on_phones():
    assert "step.view" in TOUR_JS and "view: () => summaryView(" in APP_JS
    for part in ("summary-title", "summary-visual", "gauge(", "scoreRows(", "time-chip", "richText("):
        assert part in APP_JS, part
    width = int(re.search(r"\.tour-card\.is-view \{[^}]*?width: min\((\d+)px", CSS).group(1))
    assert width >= 760  # landscape, not a narrow column
    assert re.search(r"\.summary \{[^}]*grid-template-columns: minmax\(0, [\d.]+fr\) minmax\(0, [\d.]+fr\)", CSS)
    phone = CSS[CSS.index("@media (max-width: 720px)"):]
    assert ".summary { grid-template-columns: 1fr;" in phone and ".tour-card.is-view { width: auto;" in phone


def test_summary_text_has_spacing_and_hierarchy():
    title = int(re.search(r"\.summary-title \{[^}]*?font-size: (\d+)px", CSS).group(1))
    body = float(re.search(r"\.summary-section p \{[^}]*?font-size: ([\d.]+)px; line-height: ([\d.]+)", CSS).group(1))
    line_height = float(re.search(r"\.summary-section p \{[^}]*?line-height: ([\d.]+)", CSS).group(1))
    assert title >= 26 and title / body >= 1.6  # the headline clearly outranks the body text
    assert line_height >= 1.6  # airy lines


def test_segmented_buttons_slide_a_highlight_and_keep_sliding_under_reduced_motion():
    assert "function placeThumb" in APP_JS and "ResizeObserver" in APP_JS
    assert "placeThumb(input.closest('.segmented'))" in APP_JS  # also when a guided example fills the form
    assert re.search(r"\.segmented\[data-ready\] \.thumb \{[^}]*transition: transform", CSS)
    assert ".segmented.is-instant .thumb { transition: none; }" in CSS  # first placement and resizes do not animate
    reduced = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
    assert ".segmented .thumb { transition: transform" in reduced
