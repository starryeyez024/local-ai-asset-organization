"""Opt-in browser checks: RUN_BROWSER_TESTS=1 python3 -B -m unittest discover -s tests."""

from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest


REPO = Path(__file__).resolve().parents[1]
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(directory)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


@unittest.skipUnless(os.environ.get("RUN_BROWSER_TESTS") == "1" and sync_playwright,
                     "Set RUN_BROWSER_TESTS=1 and install Playwright Chromium to run browser checks")
class ExplorerBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.personal = Path(cls.temp.name)
        for name in ("index.html", "about.html"):
            shutil.copyfile(REPO / "skills-explorer" / name, cls.personal / name)
        cls.sample = json.loads((REPO / "skills-explorer/sample-skills.json").read_text())
        cls.sample_scripts = json.loads((REPO / "skills-explorer/sample-scripts.json").read_text())
        cls.generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cls.write_personal(cls.sample["skills"][:1])
        cls.personal_server, cls.personal_url = serve(cls.personal)
        cls.demo_server, cls.demo_url = serve(REPO)
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.personal_server.shutdown()
        cls.demo_server.shutdown()
        cls.personal_server.server_close()
        cls.demo_server.server_close()
        cls.temp.cleanup()

    @classmethod
    def write_personal(cls, skills):
        data = {**cls.sample, "catalogType": "personal", "skills": skills,
                "skillCount": len(skills), "activeCount": len(skills),
                "generatedAt": cls.generated_at,
                "scannedDirectory": "/fixture/chosen-skills",
                "inventory": [{"name": skill["id"], "truePath": f"/fixture/{skill['id']}",
                               "broken": False, "hasSkillMd": True, "hasDuplicateIssue": False,
                               "duplicates": {"redundantSymlinks": [], "nameCollisions": []},
                               "inCuratedView": True, "daysSinceModified": 0}
                              for skill in skills],
                "inventoryStats": {"total": len(skills), "broken": 0, "duplicateIssues": 0,
                                   "staleThresholdDays": 60}}
        (cls.personal / "skills-local.json").write_text(json.dumps(data))
        (cls.personal / "scripts-local.json").write_text(json.dumps({"scripts": []}))

    def page(self, width=1280):
        page = self.browser.new_page(viewport={"width": width, "height": 900})
        self.addCleanup(page.close)
        return page

    def test_personal_browse_audit_source_and_refresh_time(self):
        page = self.page()
        page.goto(self.personal_url + "/index.html")
        self.assertIn("1 / 1 skills", page.locator("#results-count").inner_text())
        expected_time = page.evaluate("""timestamp => new Intl.DateTimeFormat(undefined, {
            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
        }).format(new Date(timestamp))""", self.generated_at)
        self.assertIn(f"Last refreshed {expected_time}", page.locator("#results-count").inner_text())
        self.assertFalse(page.locator("#audit-tab").is_hidden())
        page.locator("#audit-tab").click()
        self.assertIn("Showing 1 of 1 entries", page.locator("#maintain-results-count").inner_text())
        page.get_by_role("link", name="About").click()
        self.assertEqual(page.locator("#scan-directory-path").inner_text(), "/fixture/chosen-skills")

    def test_refresh_reloads_changed_catalog(self):
        page = self.page()
        page.goto(self.personal_url + "/index.html")
        self.assertIn("1 / 1 skills", page.locator("#results-count").inner_text())
        self.write_personal(self.sample["skills"][:2])
        self.addCleanup(self.write_personal, self.sample["skills"][:1])
        page.reload()
        self.assertIn("2 / 2 skills", page.locator("#results-count").inner_text())

    def test_empty_personal_catalog_has_useful_empty_states(self):
        self.write_personal([])
        self.addCleanup(self.write_personal, self.sample["skills"][:1])
        page = self.page()
        page.goto(self.personal_url + "/index.html")
        self.assertIn("0 / 0 skills", page.locator("#results-count").inner_text())
        self.assertIn("No assets match", page.locator("#skills-list").inner_text())
        page.locator("#audit-tab").click()
        self.assertIn("No entries match", page.locator("#maintain-tbody").inner_text())

    def test_demo_is_fictional_and_points_to_personal_setup(self):
        page = self.page()
        page.goto(self.demo_url + "/skills-explorer/index.html")
        self.assertIn("Demo", page.locator("header h1").inner_text())
        self.assertTrue(page.locator("#audit-tab").is_hidden())
        self.assertIn("Sample catalog", page.locator("#results-count").inner_text())
        page.get_by_role("link", name="About").click()
        page.locator("#demo-about").wait_for(state="visible")
        self.assertFalse(page.locator("#demo-about").is_hidden())
        self.assertTrue(page.locator("#local-about").is_hidden())
        self.assertIn("personal", page.locator("#demo-about").inner_text().lower())

    def test_navigation_and_mobile_layouts(self):
        for width in (390, 1280):
            with self.subTest(width=width):
                page = self.page(width)
                page.goto(self.demo_url + "/pages/index.html")
                primary = page.get_by_role("navigation", name="Primary navigation")
                self.assertEqual(primary.get_by_role("link", name="Quick reference").count(), 0)
                self.assertEqual(primary.get_by_role("link", name="Agentic Config").count(), 1)
                styles = primary.locator(".site-links a").evaluate_all("""links => links.map(link => {
                    const css = getComputedStyle(link);
                    return {border: css.borderRightStyle, width: css.borderRightWidth,
                            margin: parseFloat(css.marginRight), padding: parseFloat(css.paddingRight),
                            color: css.color, transform: css.textTransform,
                            decoration: css.textDecorationLine, thickness: css.textDecorationThickness,
                            offset: css.textUnderlineOffset};
                })""")
                self.assertTrue(all(style["border"] == "none" and style["width"] == "0px"
                                    for style in styles))
                self.assertEqual(styles[0]["margin"], 11)
                self.assertEqual(styles[0]["padding"], 12)
                self.assertEqual(styles[1]["color"], "rgb(145, 189, 240)")
                self.assertTrue(all(style["transform"] == "uppercase" for style in styles))
                self.assertEqual(styles[0]["color"], "rgb(186, 213, 244)")
                self.assertEqual(styles[0]["decoration"], "underline")
                self.assertEqual(styles[0]["thickness"], "1px")
                self.assertEqual(styles[0]["offset"], "7px")
                primary.get_by_role("link", name="Agentic Config").hover()
                self.assertEqual(primary.get_by_role("link", name="Agentic Config").evaluate(
                    "el => getComputedStyle(el).color"), "rgb(186, 213, 244)")
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)

    def test_agentic_setup_continuation_is_a_call_to_action(self):
        for width in (390, 1280):
            with self.subTest(width=width):
                page = self.page(width)
                page.goto(self.demo_url + "/pages/agentic-setup.html")
                cta = page.locator("main .final-cta")
                self.assertIn("Continue in the same setup conversation", cta.inner_text())
                self.assertEqual(cta.get_by_role("link", name="Audit and organize your assets")
                                 .get_attribute("href"), "asset-organization.html")
                self.assertEqual(cta.get_by_role("link", name="See the full workflow").count(), 0)
                self.assertNotIn("Continue in the same setup conversation", page.locator("footer").inner_text())
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)

    def test_guides_follow_linear_next_steps(self):
        for width in (390, 1280):
            with self.subTest(width=width):
                page = self.page(width)
                page.goto(self.demo_url + "/pages/index.html")
                page.locator("main").get_by_role("link", name="Agentic setup", exact=True).click()
                self.assertTrue(page.url.endswith("/pages/agentic-setup.html"))
                agentic_cta = page.locator("main .final-cta")
                self.assertEqual(agentic_cta.get_by_role("link").count(), 1)
                agentic_cta.get_by_role("link").click()
                self.assertTrue(page.url.endswith("/pages/asset-organization.html"))
                asset_cta = page.locator("main .final-cta")
                self.assertEqual(asset_cta.get_by_role("link").count(), 1)
                asset_cta.get_by_role("link").click()
                self.assertTrue(page.url.endswith("/pages/skills-explorer-guide.html"))

    def test_guide_call_to_action_and_footer_theme(self):
        for width in (390, 1280):
            with self.subTest(width=width):
                page = self.page(width)
                page.goto(self.demo_url + "/pages/skills-explorer-guide.html")
                brand = page.locator(".site-brand")
                self.assertEqual(brand.inner_text(), "AI Asset Navigation")
                self.assertGreaterEqual(brand.evaluate("el => parseFloat(getComputedStyle(el).fontSize)"), 21)
                self.assertIn("RedHatDisplay", brand.evaluate("el => getComputedStyle(el).fontFamily"))
                weights = page.locator(".site-links a").evaluate_all(
                    "links => links.map(link => getComputedStyle(link).fontWeight)")
                self.assertTrue(all(weight == "500" for weight in weights))
                main_fonts = page.locator(".site-links a").evaluate_all(
                    "links => links.map(link => getComputedStyle(link).fontFamily)")
                self.assertTrue(all("RedHatDisplay" in family for family in main_fonts))
                hero_size = page.locator(".hero h1").evaluate(
                    "el => parseFloat(getComputedStyle(el).fontSize)")
                self.assertLessEqual(hero_size, 35 if width == 390 else 47)
                cta = page.locator("main .final-cta")
                self.assertIn("Ready to begin?", cta.inner_text())
                self.assertEqual(cta.get_by_role("link", name="Start the guided setup").get_attribute("href"),
                                 "index.html#start-here")
                footer = page.locator("footer")
                self.assertNotIn("Ready to begin?", footer.inner_text())
                theme = footer.evaluate("""el => {
                    const css = getComputedStyle(el);
                    return {background: css.backgroundColor, color: css.color,
                            top: parseFloat(css.paddingTop), bottom: parseFloat(css.paddingBottom)};
                }""")
                self.assertEqual(theme["background"], "rgb(85, 93, 101)")
                self.assertEqual(theme["color"], "rgb(255, 255, 255)")
                self.assertGreaterEqual(theme["top"], 64)
                self.assertGreaterEqual(theme["bottom"], 72)
                self.assertEqual(footer.locator("a").first.evaluate(
                    "el => getComputedStyle(el).color"), "rgb(255, 255, 255)")
                footer_fonts = footer.locator(".footer-nav a").evaluate_all(
                    "links => links.map(link => getComputedStyle(link).fontFamily)")
                self.assertTrue(all("RedHatDisplay" in family for family in footer_fonts))
                if width == 390:
                    contribute_offset = footer.locator("#feedback-link").evaluate("""link => {
                        const nav = link.closest('nav').getBoundingClientRect();
                        const item = link.getBoundingClientRect();
                        return Math.abs((item.left + item.right) / 2 - (nav.left + nav.right) / 2);
                    }""")
                    self.assertLessEqual(contribute_offset, 2)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                footer = page.get_by_role("navigation", name="Footer navigation")
                self.assertEqual(footer.get_by_role("link", name="Contribute").count(), 1)
                footer_styles = footer.locator("a").evaluate_all("""links => links.map(link => {
                    const css = getComputedStyle(link);
                    return {border: css.borderRightStyle, margin: parseFloat(css.marginRight),
                            padding: parseFloat(css.paddingRight)};
                })""")
                self.assertEqual(footer_styles[0]["border"], "solid")
                self.assertGreaterEqual(footer_styles[0]["margin"], 22)
                self.assertGreaterEqual(footer_styles[0]["padding"], 22)
                self.assertEqual(footer_styles[1]["border"], "none" if width == 390 else "solid")
                self.assertEqual(footer_styles[2]["border"], "none")
                alignment = footer.evaluate("""nav => {
                    const navBox = nav.getBoundingClientRect();
                    const links = [...nav.querySelectorAll('a')].map(link => link.getBoundingClientRect());
                    const groupCenter = (Math.min(...links.map(box => box.left)) +
                                         Math.max(...links.map(box => box.right))) / 2;
                    return Math.abs(groupCenter - (navBox.left + navBox.right) / 2);
                }""")
                self.assertLessEqual(alignment, 2)
                footer.get_by_role("link", name="Quick reference").click()
                self.assertIn("Quick reference", page.locator("h1").inner_text())
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.goto(self.demo_url + "/skills-explorer/index.html")
                if width == 390:
                    self.assertFalse(page.locator("#mobile-filter-toggle").is_hidden())
                    page.wait_for_function("document.querySelector('#mobile-filter-toggle').getAttribute('aria-expanded') === 'false'")
                    page.locator("#mobile-filter-toggle").click()
                    self.assertEqual(page.locator("#mobile-filter-toggle").get_attribute("aria-expanded"), "true")
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)


if __name__ == "__main__":
    unittest.main()
