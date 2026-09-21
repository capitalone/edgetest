"""Tests for format-preserving requirement upgrades (issue #80).

Covers the specifier-only replacement helpers and the widen-only rule:
a tested version that already satisfies a bound leaves the file untouched;
only violated bounds are widened, and never with a synthesized ``!=``.
"""

import pytest

from edgetest.utils import (
    _split_inline_comment,
    _split_marker,
    _upgrade_requirement_line,
    _widen_specifier,
    upgrade_requirements,
)


class TestSplitInlineComment:
    @pytest.mark.parametrize(
        ("line", "code", "comment"),
        [
            ("numpy>=1.0", "numpy>=1.0", ""),
            ("numpy>=1.0  # note", "numpy>=1.0  ", "# note"),
            ("# full line", "", "# full line"),
            (
                "pkg>=1.0; extra == '#notacomment'",
                "pkg>=1.0; extra == '#notacomment'",
                "",
            ),
            (
                'pkg>=1.0; extra == "#notacomment"',
                'pkg>=1.0; extra == "#notacomment"',
                "",
            ),
            (
                "pkg>=1.0  # 'quoted inside comment",
                "pkg>=1.0  ",
                "# 'quoted inside comment",
            ),
        ],
    )
    def test_split(self, line, code, comment):
        assert _split_inline_comment(line) == (code, comment)

    def test_rejoin_is_identity(self):
        for line in [
            "numpy>=1.0",
            "numpy>=1.0  # note",
            "  # indented comment",
            "pkg>=1.0; extra == '#x'",
            "",
        ]:
            code, comment = _split_inline_comment(line)
            assert code + comment == line


class TestSplitMarker:
    @pytest.mark.parametrize(
        ("text", "specs", "marker"),
        [
            (">=1.0,<2.0", ">=1.0,<2.0", ""),
            (">=1.0; python_version<'3.12'", ">=1.0", "; python_version<'3.12'"),
            ('; extra == "tests"', "", '; extra == "tests"'),
        ],
    )
    def test_split(self, text, specs, marker):
        assert _split_marker(text) == (specs, marker)

    def test_rejoin_is_identity(self):
        for text in [">=1.0,<2.0", ">=1.0 ; x", "; extra == 'tests'"]:
            specs, marker = _split_marker(text)
            assert specs + marker == text


class TestWidenSpecifier:
    # --- already satisfied: unchanged (the widen-only core) ---
    @pytest.mark.parametrize(
        ("spec", "tested"),
        [
            ("<2.6", "2.5.3"),
            ("<=2.5.3", "2.5.3"),
            (">=1.26.4", "2.5.3"),
            ("~=1.4", "1.7"),
            ("!=4", "4.0.0"),  # user exclusion never modified
            ("!=4", "5.0.0"),
            ("==1.0", "1.0"),
        ],
    )
    def test_satisfied_unchanged(self, spec, tested):
        assert _widen_specifier(spec, tested) == [spec]

    # --- violated: widened, never with a synthesized != ---
    @pytest.mark.parametrize(
        ("spec", "tested", "expected"),
        [
            ("<2.6", "2.6.0", ["<=2.6.0"]),
            ("<2.6", "3.1.0", ["<=3.1.0"]),
            ("<=2.5.3", "2.6.0", ["<=2.6.0"]),
            ("==1.0", "2.0", [">=1.0", "<=2.0"]),
            ("~=1.4", "2.0", [">=1.4", "<=2.0"]),
            (">2.0", "1.5", [">=1.5"]),
            (">=2.0", "1.5", [">=1.5"]),
        ],
    )
    def test_violated_widened(self, spec, tested, expected):
        assert _widen_specifier(spec, tested) == expected

    def test_no_bang_equals_synthesized(self):
        for tested in ["2.6.0", "3.0.0"]:
            out = _widen_specifier("<2.6", tested)
            assert all("!=" not in s for s in out)


class TestUpgradeRequirementLine:
    def test_satisfied_line_is_byte_identical(self):
        line = "numpy>=1.26.4,<2.6"
        assert _upgrade_requirement_line(line, "2.5.3") == line

    def test_violated_upper_bound_widened_in_place(self):
        assert (
            _upgrade_requirement_line("numpy>=1.26.4,<2.6", "2.6.0")
            == "numpy>=1.26.4,<=2.6.0"
        )

    def test_order_preserved(self):
        # old code sorted alphabetically via SpecifierSet; we keep input order
        out = _upgrade_requirement_line("pkg>=1.0,<2.0", "2.5")
        assert out == "pkg>=1.0,<=2.5"
        assert out.index(">=") < out.index("<=")

    def test_extras_preserved(self):
        out = _upgrade_requirement_line("polars[pandas]>=0.20.4,<1.45", "1.45.0")
        assert out == "polars[pandas]>=0.20.4,<=1.45.0"

    def test_space_before_extras_does_not_crash(self):
        out = _upgrade_requirement_line("pkg [extra] >=1.0,<2.0", "2.5")
        assert out == "pkg [extra] >=1.0,<=2.5"

    def test_space_before_extras_satisfied_unchanged(self):
        line = "pkg [extra] >=1.0,<2.0"
        assert _upgrade_requirement_line(line, "1.5") == line

    def test_multiple_spaces_before_extras_preserved(self):
        out = _upgrade_requirement_line("pkg  [a,b]  >=1.0,<2.0", "2.5")
        assert out == "pkg  [a,b]  >=1.0,<=2.5"

    def test_space_after_name_no_extras(self):
        out = _upgrade_requirement_line("pkg >=1.0,<2.0", "2.5")
        assert out == "pkg >=1.0,<=2.5"

    def test_marker_preserved(self):
        out = _upgrade_requirement_line("pkg>=1.0,<2.0; python_version<'3.12'", "2.5")
        assert out == "pkg>=1.0,<=2.5; python_version<'3.12'"

    def test_inline_comment_preserved_with_spacing(self):
        out = _upgrade_requirement_line("pandas>=1.5.1,<=2.0.0  # keep an eye", "2.3.2")
        assert out == "pandas>=1.5.1,<=2.3.2  # keep an eye"

    def test_spacing_around_operators_preserved(self):
        out = _upgrade_requirement_line("numpy >= 1.26.4 , < 2.6", "2.6.0")
        assert out == "numpy >= 1.26.4 , <=2.6.0"

    def test_leading_indent_preserved(self):
        out = _upgrade_requirement_line("    numpy<2.6", "2.6.0")
        assert out == "    numpy<=2.6.0"

    def test_direct_url_untouched(self):
        line = "pkg @ https://example.com/pkg-1.0.whl"
        assert _upgrade_requirement_line(line, "2.0") == line

    def test_no_specifier_untouched(self):
        assert _upgrade_requirement_line("numpy", "2.6.0") == "numpy"

    def test_mixed_case_name_preserved(self):
        out = _upgrade_requirement_line("NumPy>=1.0,<2.0", "2.5")
        assert out == "NumPy>=1.0,<=2.5"


class TestUpgradeRequirements:
    def test_empty_upgrade_list_is_identity(self):
        content = (
            "# core deps\n"
            "numpy>=1.26.4,<2.6  # pinned range\n"
            "\n"
            "-r other.txt\n"
            "pandas[excel]>=2.0; python_version>='3.10'\n"
        )
        assert upgrade_requirements(content, []) == content

    def test_satisfied_upgrades_produce_no_change(self):
        content = "numpy>=1.26.4,<2.6\npandas>=2.0,<=2.3.2\n"
        upgrades = [
            {"name": "numpy", "version": "2.5.3"},
            {"name": "pandas", "version": "2.3.2"},
        ]
        assert upgrade_requirements(content, upgrades) == content

    def test_comments_blanks_and_options_pass_through(self):
        content = (
            "# header\n"
            "\n"
            "-r base.txt\n"
            "--index-url https://example.com/simple\n"
            "numpy<2.0\n"
            "  # trailing indented comment\n"
        )
        out = upgrade_requirements(content, [{"name": "numpy", "version": "2.5"}])
        lines = out.splitlines()
        assert lines[0] == "# header"
        assert lines[1] == ""
        assert lines[2] == "-r base.txt"
        assert lines[3] == "--index-url https://example.com/simple"
        assert lines[4] == "numpy<=2.5"
        assert lines[5] == "  # trailing indented comment"

    def test_substring_trap(self):
        content = "numpydoc>=1.0\nnumpy>=1.0,<2.0\nnumpy-stubs>=1.0\n"
        out = upgrade_requirements(content, [{"name": "numpy", "version": "2.5"}])
        assert out == "numpydoc>=1.0\nnumpy>=1.0,<=2.5\nnumpy-stubs>=1.0\n"

    def test_case_insensitive_match(self):
        out = upgrade_requirements(
            "NumPy>=1.0,<2.0", [{"name": "numpy", "version": "2.5"}]
        )
        assert out == "NumPy>=1.0,<=2.5"

    def test_idempotent(self):
        content = "numpy>=1.26.4,<2.6\n"
        upgrades = [{"name": "numpy", "version": "2.6.0"}]
        once = upgrade_requirements(content, upgrades)
        twice = upgrade_requirements(once, upgrades)
        assert once == twice == "numpy>=1.26.4,<=2.6.0\n"

    def test_final_newline_presence_preserved(self):
        with_nl = "numpy<2.0\n"
        without_nl = "numpy<2.0"
        upgrades = [{"name": "numpy", "version": "2.5"}]
        assert upgrade_requirements(with_nl, upgrades).endswith("\n")
        assert not upgrade_requirements(without_nl, upgrades).endswith("\n")

    def test_crlf_line_endings_preserved(self):
        content = "numpy<2.0\r\npandas<3.0\r\n"
        upgrades = [
            {"name": "numpy", "version": "2.5"},
            {"name": "pandas", "version": "3.1"},
        ]
        out = upgrade_requirements(content, upgrades)
        assert out == "numpy<=2.5\r\npandas<=3.1\r\n"

    def test_dash_underscore_equivalence(self):
        out = upgrade_requirements(
            "python_dateutil>=2.0,<3.0",
            [{"name": "python-dateutil", "version": "3.1"}],
        )
        assert out == "python_dateutil>=2.0,<=3.1"

    def test_multiple_upgrades_minimal_diff(self):
        content = "numpy>=1.26.4,<2.6\npandas>=2.0,<3.0\nscipy>=1.10\n"
        upgrades = [{"name": "pandas", "version": "3.2"}]
        out = upgrade_requirements(content, upgrades)
        lines_in = content.splitlines()
        lines_out = out.splitlines()
        changed = [
            i
            for i, (a, b) in enumerate(zip(lines_in, lines_out, strict=True))
            if a != b
        ]
        assert changed == [1]  # only the pandas line changed
