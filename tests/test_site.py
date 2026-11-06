"""Local-only site tests; synthetic report/results stay in temporary directories."""

from importlib.metadata import version
from pathlib import Path
import tempfile
import unittest

from tools import build_site, check_site


REPORT = '''---
title: A bounded report
status: local
---
# A bounded report

[Results](data/results.json) and [limitations](#threats-to-validity).

## Retained failures

The pilot failed. No improvement was demonstrated.

```text
gain(t) = |S| - max_o |B(t,o)|
```

| Check | Passed |
| --- | ---: |
| Example | 1 |

## Threats to validity

This is not sufficient for full reproduction.
'''
RESULTS = b'{\n  "aggregate": {"passed": 1, "failed": 1}\n}\n'


class FrontmatterTests(unittest.TestCase):
    def test_frontmatter_stripped_without_body_rewrite(self):
        metadata, body = build_site.split_frontmatter(REPORT)
        self.assertEqual(metadata["title"], "A bounded report")
        self.assertEqual(body, REPORT.split("---\n", 2)[2])
        self.assertNotIn("status: local", build_site.render_report(REPORT))

    def test_no_frontmatter(self):
        body = "# Report\n\nText\n---\nMore text\n"
        self.assertEqual(build_site.split_frontmatter(body), ({}, body))

    def test_crlf_and_yaml_end_marker(self):
        self.assertEqual(
            build_site.split_frontmatter("---\r\ntitle: Example\r\n...\r\n# Heading\r\n"),
            ({"title": "Example"}, "# Heading\r\n"),
        )

    def test_unclosed_frontmatter(self):
        with self.assertRaisesRegex(build_site.SiteError, "Unclosed"):
            build_site.split_frontmatter("---\ntitle: missing terminator\n")

    def test_title_precedes_collapsed_contents(self):
        page = build_site.render_report(REPORT)
        self.assertLess(page.index("<h1"), page.index("<nav"))
        self.assertIn("<details>", page)
        self.assertNotIn("<details open", page)

    def test_metadata_is_escaped(self):
        page = build_site.render_report(REPORT.replace("title: A bounded report", 'title: <script>"&</script>'))
        self.assertIn("<title>&lt;script&gt;&quot;&amp;&lt;/script&gt;</title>", page)
        self.assertNotIn("<script>", page)
        self.assertEqual(check_site.Page(page).h1_count, 1)

    def test_renderer_features_and_pin(self):
        self.assertEqual(version("Markdown"), "3.8.2")
        page = build_site.render_report(REPORT)
        self.assertIn('<h2 id="retained-failures">', page)
        self.assertIn('href="#retained-failures"', page)
        self.assertIn('<pre tabindex="0"><code class="language-text">', page)
        self.assertIn('<td class="align-right">1</td>', page)
        self.assertIn('class="table-scroll"', page)


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "data").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "report.md").write_text(REPORT, encoding="utf-8")
        (self.root / "data/results.json").write_bytes(RESULTS)
        css = Path(__file__).resolve().parents[1] / "docs/style.css"
        (self.root / "docs/style.css").write_bytes(css.read_bytes())

    def build(self):
        build_site.build(self.root)

    def change_html(self, old, new):
        path = self.root / "docs/index.html"
        page = path.read_text(encoding="utf-8")
        self.assertIn(old, page)
        path.write_text(page.replace(old, new), encoding="utf-8")

    def test_build_and_check_deterministic_byte_exact_copy(self):
        self.build()
        first = {path: (self.root / path).read_bytes() for path in build_site.expected_files(self.root)}
        self.build()
        second = {path: (self.root / path).read_bytes() for path in first}
        self.assertEqual(first, second)
        self.assertEqual((self.root / "docs/data/results.json").read_bytes(), RESULTS)
        self.assertEqual((self.root / "docs/.nojekyll").read_bytes(), b"")
        check_site.check_site(self.root)

    def test_missing_results_fails_before_creating_site(self):
        (self.root / "data/results.json").unlink()
        with self.assertRaisesRegex(build_site.SiteError, "Missing required input: data/results.json"):
            self.build()
        self.assertFalse((self.root / "docs/index.html").exists())

    def test_missing_report_fails(self):
        (self.root / "report.md").unlink()
        with self.assertRaisesRegex(build_site.SiteError, "report.md"):
            self.build()

    def test_invalid_json_refused(self):
        for bad in (b'{"partial":', b'{"value": NaN}', b'\xff'):
            with self.subTest(bad=bad):
                (self.root / "data/results.json").write_bytes(bad)
                with self.assertRaisesRegex(build_site.SiteError, "Invalid UTF-8 JSON"):
                    self.build()

    def test_invalid_report_encoding_refused(self):
        (self.root / "report.md").write_bytes(b"\xff")
        with self.assertRaisesRegex(build_site.SiteError, "UTF-8"):
            self.build()

    def test_source_change_detects_stale_site(self):
        self.build()
        with (self.root / "report.md").open("a", encoding="utf-8") as source:
            source.write("\nAdditional limitation.\n")
        with self.assertRaisesRegex(build_site.SiteError, "Stale generated site: docs/index.html"):
            check_site.check_site(self.root)

    def test_aggregate_change_detects_stale_copy(self):
        self.build()
        (self.root / "data/results.json").write_bytes(b'{"changed": true}\n')
        with self.assertRaisesRegex(build_site.SiteError, "Stale generated site: docs/data/results.json"):
            check_site.check_site(self.root)

    def test_generated_edit_detects_stale_html(self):
        self.build()
        self.change_html("A bounded report", "An edited report")
        with self.assertRaisesRegex(build_site.SiteError, "Stale generated site"):
            check_site.check_site(self.root)

    def test_missing_nojekyll_detected(self):
        self.build()
        (self.root / "docs/.nojekyll").unlink()
        with self.assertRaisesRegex(build_site.SiteError, "docs/.nojekyll"):
            check_site.check_site(self.root)

    def test_local_assets_and_fragments_resolve(self):
        self.build()
        for reference in ("style.css", "data/results.json", "#threats-to-validity", "index.html#report"):
            with self.subTest(reference=reference):
                check_site.check_reference(self.root, "docs/index.html", reference, True)
        for reference in ("missing.css", "#missing", "data/results.json#missing"):
            with self.subTest(reference=reference), self.assertRaises(build_site.SiteError):
                check_site.check_reference(self.root, "docs/index.html", reference, True)

    def test_broken_fragment_in_page_rejected(self):
        self.build()
        self.change_html('href="#threats-to-validity"', 'href="#absent"')
        with self.assertRaisesRegex(build_site.SiteError, "Unresolved fragment"):
            check_site.check_site(self.root)

    def test_traversal_refused(self):
        for path in ("../report.md", "/etc/passwd", "docs/../report.md", "docs//index.html", "docs\\index.html", "docs/./index.html", "docs/\0file"):
            with self.subTest(path=path), self.assertRaises(build_site.SiteError):
                build_site.safe_path(self.root, path)

    def test_url_traversal_and_unsafe_schemes_refused(self):
        self.build()
        for reference in ("../report.md", "%2e%2e/report.md", "%2Fetc/passwd", "data/%2e%2e/results.json", "data%5cresults.json", "//example.com/file", "file:///etc/passwd", "javascript:alert(1)"):
            with self.subTest(reference=reference), self.assertRaises(build_site.SiteError):
                check_site.check_reference(self.root, "docs/index.html", reference, True)
        with self.assertRaisesRegex(build_site.SiteError, "External/unsafe asset"):
            check_site.check_reference(self.root, "docs/index.html", "https://example.com/style.css", False)
        # Ordinary bibliography links are allowed without making network requests.
        check_site.check_reference(self.root, "docs/index.html", "https://example.com/paper#section", True)

    def test_symlinked_input_and_output_refused(self):
        (self.root / "data/results.json").unlink()
        (self.root / "data/results.json").symlink_to(self.root / "report.md")
        with self.assertRaisesRegex(build_site.SiteError, "Symlink refused"):
            self.build()
        (self.root / "data/results.json").unlink()
        (self.root / "data/results.json").write_bytes(RESULTS)
        (self.root / "docs/data").symlink_to(self.root / "data", target_is_directory=True)
        with self.assertRaisesRegex(build_site.SiteError, "Symlink refused"):
            self.build()
        self.assertFalse((self.root / "docs/index.html").exists())

    def test_h1_count_and_duplicate_ids(self):
        self.build()
        self.change_html("</main>", '<h1 id="extra">Extra</h1></main>')
        with self.assertRaisesRegex(build_site.SiteError, "exactly one h1"):
            check_site.check_site(self.root)
        self.build()
        self.change_html("</main>", '<p id="report">Duplicate</p></main>')
        with self.assertRaisesRegex(build_site.SiteError, "duplicate fragment"):
            check_site.check_site(self.root)

    def test_negative_evidence_and_limitations_required(self):
        cases = (
            (REPORT.replace("pilot failed", "pilot succeeded").replace("Retained failures", "Observations"), "failure evidence"),
            (REPORT.replace("Threats to validity", "Scope").replace("threats-to-validity", "scope").replace("limitations", "scope"), "limitations"),
            (REPORT.replace("No improvement", "Improvement").replace("not sufficient", "sufficient"), "negative qualifications"),
        )
        for text, error in cases:
            with self.subTest(error=error):
                (self.root / "report.md").write_text(text, encoding="utf-8")
                self.build()
                with self.assertRaisesRegex(build_site.SiteError, error):
                    check_site.check_site(self.root)

    def test_active_content_refused(self):
        for addition in ('<script>alert(1)</script>', '<img src="data/results.json" onerror="alert(1)">', '<iframe src="index.html"></iframe>', '<meta http-equiv="refresh" content="0">'):
            with self.subTest(addition=addition), self.assertRaises(build_site.SiteError):
                check_site.Page(build_site.render_report(REPORT) + addition)

    def test_duplicate_attributes_cannot_hide_active_links_or_assets(self):
        for addition in ('<a href="javascript:alert(1)" href="#report">Click</a>', '<img src="https://example.com/tracker" src="data/results.json">'):
            with self.subTest(addition=addition):
                (self.root / "report.md").write_text(REPORT + addition, encoding="utf-8")
                self.build()
                with self.assertRaisesRegex(build_site.SiteError, "Duplicate HTML attributes"):
                    check_site.check_site(self.root)

    def test_unexpected_private_artifact_refused(self):
        self.build()
        (self.root / "docs/trace.jsonl").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(build_site.SiteError, "Unexpected site artifact"):
            check_site.check_site(self.root)

    def test_private_paths_and_credentials_refused(self):
        for private in ("/" + "home" + "/example/run", "private.local/results", ".venv/bin/python", "ghp_" + "x" * 30):
            with self.subTest(private=private):
                (self.root / "data/results.json").write_text('{"private": "' + private + '"}', encoding="utf-8")
                self.build()
                with self.assertRaises(build_site.SiteError):
                    check_site.check_site(self.root)

    def test_css_cannot_add_network_imports(self):
        self.build()
        path = self.root / "docs/style.css"
        original = path.read_text(encoding="utf-8")
        for addition in ('@import "https://example.com/font.css";', r'@\69mport "https://example.com/font.css";', 'p { background: url(https://example.com/pixel); }'):
            with self.subTest(addition=addition):
                path.write_text(original + "\n" + addition, encoding="utf-8")
                with self.assertRaisesRegex(build_site.SiteError, "Stylesheet must not import"):
                    check_site.check_site(self.root)


if __name__ == "__main__":
    unittest.main()
