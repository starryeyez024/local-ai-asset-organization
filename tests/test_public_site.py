"""Guard the published demo and the guides' common entry points."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


REPO = Path(__file__).resolve().parents[1]
PAGES = REPO / "pages"
EXPLORER = REPO / "skills-explorer"
GUIDES = ("index.html", "agentic-setup.html", "asset-organization.html",
          "tool-compatibility.html", "skills-explorer-guide.html", "quick-reference.html")


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


class PublicSite(unittest.TestCase):
    def test_guides_have_consistent_navigation_and_local_targets(self):
        for name in GUIDES:
            with self.subTest(page=name):
                source = (PAGES / name).read_text()
                self.assertIn('name="viewport"', source)
                self.assertIn("Quick reference", source)
                self.assertTrue("agent-setup" in source or "index.html#start-here" in source)
                primary = source.split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]
                footer = source.split('<nav class="footer-nav"', 1)[1].split("</nav>", 1)[0]
                self.assertNotIn("Compatibility</a>", primary)
                self.assertNotIn("Quick reference</a>", primary)
                for label in ("Compatibility", "Quick reference", "Contribute"):
                    self.assertIn(f">{label}</a>", footer)
                self.assertNotIn("Have feedback or an idea?", source)
                parser = PageLinks()
                parser.feed(source)
                targets = {link.get("href") for link in parser.links}
                self.assertIn("quick-reference.html", targets)
                self.assertIn("index.html", targets)
                for link in parser.links:
                    local = link.get("data-local-href", link.get("href", ""))
                    path = urlsplit(local).path
                    if not path or path.startswith("/") or urlsplit(local).scheme:
                        continue
                    self.assertTrue((PAGES / path).exists() or (REPO / path).exists(),
                                    f"{name}: broken local link {local}")
        self.assertNotIn("A general methodology for organizing AI agent assets across multiple tools and runtimes",
                         (PAGES / "index.html").read_text())

    def test_demo_catalog_is_fictional_and_has_no_private_paths(self):
        skills = json.loads((EXPLORER / "sample-skills.json").read_text())
        scripts = json.loads((EXPLORER / "sample-scripts.json").read_text())
        self.assertEqual(skills["catalogType"], "demo")
        self.assertEqual(scripts["catalogType"], "demo")
        self.assertEqual(skills["skillCount"], len(skills["skills"]))
        self.assertNotIn("inventory", skills)
        self.assertNotIn("scannedDirectory", skills)
        self.assertEqual({skill["id"] for skill in skills["skills"]},
                         {"draft-status-update", "summarize-meeting", "review-project-plan"})
        self.assertEqual({script["id"] for script in scripts["scripts"]},
                         {"example-automation/morning-report", "example-automation/data-check"})
        for script in scripts["scripts"]:
            self.assertFalse(script["file"])
            self.assertFalse(script["workingDirectory"])
        serialized = json.dumps((skills, scripts))
        self.assertIsNone(re.search(r"/Users/|/home/|[A-Za-z]:\\\\Users\\\\|ktotten|redhat\.com", serialized,
                                    re.IGNORECASE))

    def test_publish_manifest_excludes_personal_catalogs_and_server(self):
        pipeline = (REPO / ".gitlab-ci.yml").read_text()
        explorer_copy = next(line for line in pipeline.splitlines()
                             if "cp skills-explorer/index.html" in line)
        for required in ("index.html", "about.html", "sample-skills.json", "sample-scripts.json"):
            self.assertIn(required, explorer_copy)
        for private in ("skills.json", "skills-local.json", "scripts-local.json", "serve.py"):
            self.assertNotIn(f"skills-explorer/{private}", explorer_copy)
        self.assertNotIn("cp -r skills-explorer", pipeline)
        self.assertIn("personal Explorer", (EXPLORER / "about.html").read_text())


if __name__ == "__main__":
    unittest.main()
