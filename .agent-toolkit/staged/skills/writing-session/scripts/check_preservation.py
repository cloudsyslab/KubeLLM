#!/usr/bin/env python3
"""Conservative Markdown preservation-drift checker.

This guardrail reports changed protected details for author review.  A clean
result is not a claim that two documents mean the same thing.
"""

import argparse
from collections import Counter
import hashlib
import json
import re
import sys


BCP14 = re.compile(
    r"\b(?:MUST(?:\s+NOT)?|SHALL(?:\s+NOT)?|SHOULD(?:\s+NOT)?|"
    r"REQUIRED|RECOMMENDED|NOT\s+RECOMMENDED|MAY|OPTIONAL)\b"
)
LOGICAL_SCOPE = re.compile(
    r"\b(?:not|never|only|always|unless|except|none|all|each|every|"
    r"may|might|can(?:not)?|will|would|at\s+least|at\s+most|exactly|"
    r"known|unknown)\b",
    re.IGNORECASE,
)
NUMBER = re.compile(
    r"(?<![\w.])[+-]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.\d+)?"
    r"(?:\s*(?:%|‰|ns|µs|ms|seconds?|secs?|s|minutes?|mins?|m|"
    r"hours?|hrs?|h|days?|d|weeks?|w|bytes?|[kMGT]i?B|[kMGT]?bps|"
    r"[kMGT]?Hz|°[CF]|x|×))?(?!\w)"
)
STANDARD_ID = re.compile(
    r"\b(?:RFC|BCP|STD|ISO(?:/IEC)?|NIST(?:\s+SP)?|IEEE|FIPS)\s+"
    r"[A-Za-z0-9][A-Za-z0-9./-]*\b"
)
TICKET_ID = re.compile(r"\b[A-Z][A-Z0-9]{1,12}-\d{1,8}\b")
QUALIFIED_ID = re.compile(r"\b[A-Za-z_]\w*(?:::\w+)+\b")


def squash(value):
    """Normalize only whitespace; preservation checks deliberately stay strict."""
    return " ".join(value.strip().split())


def preview(value, limit=140):
    value = squash(value)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def separate_fences(text):
    """Return non-code text (with line positions retained) and fenced blocks."""
    visible, blocks, fence, content = [], [], None, []
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence is None and marker:
            fence = (marker.group(1)[0], len(marker.group(1)), marker.group(2).strip())
            content = []
            visible.append("")
        elif fence and re.match(r"^\s*" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*$", line):
            blocks.append((fence[2], "\n".join(content), True))
            fence, content = None, []
            visible.append("")
        elif fence:
            content.append(line)
            visible.append("")
        else:
            visible.append(line)
    if fence:
        blocks.append((fence[2], "\n".join(content), False))
    return "\n".join(visible), blocks


def normative_lines(text):
    """Keep the whole sentence/line so a changed NOT remains visible in review."""
    found = []
    for line in text.splitlines():
        for match in BCP14.finditer(line):
            start = max(line.rfind(mark, 0, match.start()) for mark in ".?!") + 1
            ends = [line.find(mark, match.end()) for mark in ".?!"]
            end = min((point for point in ends if point >= 0), default=len(line)) + 1
            sentence = squash(line[start:end])
            if sentence:
                found.append(sentence)
    return found


def logical_scope_lines(text):
    """Flag edits to non-BCP negation, quantifiers, and epistemic modality."""
    return [squash(line) for line in text.splitlines() if LOGICAL_SCOPE.search(line)]


def inline_code(text):
    return [match.group(2) for match in re.finditer(r"(?<!`)(`+)([^`\n]+?)\1(?!`)", text)]


def link_targets(text):
    targets = []
    for match in re.finditer(r"\]\(\s*(?:<([^>]+)>|([^\s)]+))", text):
        targets.append(match.group(1) or match.group(2))
    for match in re.finditer(r"^\s*\[[^]]+\]:\s*(?:<([^>]+)>|(\S+))", text, re.M):
        targets.append(match.group(1) or match.group(2))
    for match in re.finditer(r"<(https?://[^ >]+|mailto:[^ >]+)>", text):
        targets.append(match.group(1))
    return targets


def technical_ids(text):
    found = []
    for pattern in (STANDARD_ID, TICKET_ID, QUALIFIED_ID):
        found.extend(match.group(0) for match in pattern.finditer(text))
    return found


def headings(text):
    rows, lines = [], text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            rows.append("H%d %s" % (len(match.group(1)), squash(match.group(2))))
        elif index and re.match(r"^\s*(=+|-+)\s*$", line) and lines[index - 1].strip():
            rows.append("H%d %s" % (1 if "=" in line else 2, squash(lines[index - 1])))
    return rows


def ordered_items(text):
    rows = []
    for line in text.splitlines():
        match = re.match(r"^(\s*)(\d+)[.)]\s+(.+?)\s*$", line)
        if match:
            rows.append("%s%s. %s" % (" " * len(match.group(1)), match.group(2), squash(match.group(3))))
    return rows


def table_cells(line):
    line = line.strip()
    if "|" not in line:
        return []
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [squash(cell) for cell in line.split("|")]


def is_table_separator(cells):
    return bool(cells) and all(re.match(r"^:?-{3,}:?$", cell) for cell in cells)


def tables(text):
    rows, lines, index = [], text.splitlines(), 0
    while index + 1 < len(lines):
        header, divider = table_cells(lines[index]), table_cells(lines[index + 1])
        if header and len(header) == len(divider) and is_table_separator(divider):
            body, cursor = [], index + 2
            while cursor < len(lines):
                cells = table_cells(lines[cursor])
                if len(cells) != len(header):
                    break
                body.append(cells)
                cursor += 1
            key_index = next(
                (n for n, name in enumerate(header) if re.search(r"\b(id|key|name|identifier)\b", name, re.I)),
                0,
            )
            schema = "columns=[%s]; alignment=[%s]" % (" | ".join(header), " | ".join(divider))
            rows.append((schema, ["%s=%s" % (header[key_index], row[key_index]) for row in body]))
            index = cursor
        else:
            index += 1
    return rows


def code_blocks(blocks):
    values = []
    for language, content, closed in blocks:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        values.append(
            "language=%s; closed=%s; sha256=%s; preview=%s"
            % (language or "plain", str(closed).lower(), digest, json.dumps(preview(content)))
        )
    return values


def protected_parts(text):
    visible, blocks = separate_fences(text)
    table_rows = tables(visible)
    return {
        "normative_bcp14": normative_lines(visible),
        "logical_scope": logical_scope_lines(visible),
        "fenced_code": code_blocks(blocks),
        "inline_code": inline_code(visible),
        "link_targets": link_targets(visible),
        "technical_identifiers": technical_ids(visible),
        "numeric_values": NUMBER.findall(visible),
        "heading_hierarchy": headings(visible),
        "ordered_list_sequence": ordered_items(visible),
        "table_schemas": [schema for schema, _ in table_rows],
        "table_key_values": [key for _, keys in table_rows for key in keys],
    }


def counter_change(kind, before, after):
    old, new = Counter(before), Counter(after)
    missing, added = list((old - new).elements()), list((new - old).elements())
    if not missing and not added:
        return None
    return {
        "kind": kind,
        "message": "%s changed; inspect the source and edited artifact." % kind.replace("_", " "),
        "missing_from_after": missing,
        "added_in_after": added,
    }


def sequence_change(kind, before, after):
    if before == after:
        return None
    return {
        "kind": kind,
        "message": "%s changed in content, order, or hierarchy; inspect manually." % kind.replace("_", " "),
        "before": before,
        "after": after,
    }


def analyze_text(before_text, after_text):
    before, after, findings = protected_parts(before_text), protected_parts(after_text), []
    for kind in (
        "normative_bcp14", "logical_scope", "fenced_code", "inline_code", "link_targets",
        "technical_identifiers", "numeric_values", "table_schemas", "table_key_values",
    ):
        finding = counter_change(kind, before[kind], after[kind])
        if finding:
            findings.append(finding)
    for kind in ("heading_hierarchy", "ordered_list_sequence"):
        finding = sequence_change(kind, before[kind], after[kind])
        if finding:
            findings.append(finding)
    return findings


def render_human(result):
    status = "DRIFT DETECTED" if result["drift_detected"] else "no tracked drift detected"
    lines = ["Preservation check: %s" % status]
    for finding in result["findings"]:
        lines.append("- %s: %s" % (finding["kind"], finding["message"]))
        for label in ("missing_from_after", "added_in_after", "before", "after"):
            if finding.get(label):
                lines.append("  %s:" % label.replace("_", " "))
                lines.extend("    - %s" % item for item in finding[label])
    lines.append("Guardrail only: review findings manually; this does not assess semantic equivalence or auto-revert edits.")
    return "\n".join(lines)


def self_test():
    before = """# RFC Plan
The client MUST NOT send more than -1.5% retries within 30 s.
The actor is not known when legacy work is replayed.
See [RFC 3711](https://www.rfc-editor.org/rfc/rfc3711). Use `session_id`.
```json
{"timeout": 30}
```
1. First
2. Second
| ID | Status |
| --- | --- |
| ABC-42 | ready |
"""
    after = """## RFC Plan
The client SHOULD send more than +2% retries within 45 s.
The actor may be unknown when legacy work is replayed.
See [RFC 3711](https://example.test/rfc3711). Use `sessionId`.
```json
{"timeout": 45}
```
1. Second
2. First
| Ticket | Status |
| :--- | --- |
| ABC-43 | ready |
"""
    findings = analyze_text(before, after)
    expected = {
        "normative_bcp14", "logical_scope", "fenced_code", "inline_code", "link_targets",
        "technical_identifiers", "numeric_values", "heading_hierarchy",
        "ordered_list_sequence", "table_schemas", "table_key_values",
    }
    seen = {finding["kind"] for finding in findings}
    assert not analyze_text(before, before), "identical text must be clean"
    assert expected <= seen, "self-test missed: %s" % sorted(expected - seen)
    print("self-test passed (%d preservation categories detected)" % len(seen))


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", nargs="?", help="original Markdown file")
    parser.add_argument("after", nargs="?", help="edited Markdown file")
    parser.add_argument("--json", action="store_true", help="emit structured findings")
    parser.add_argument("--self-test", action="store_true", help="run built-in checks and exit")
    args = parser.parse_args(argv)
    if not args.self_test and (not args.before or not args.after):
        parser.error("before and after are required unless --self-test is used")
    return args


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    if args.self_test:
        self_test()
        return 0
    try:
        with open(args.before, encoding="utf-8") as source:
            before_text = source.read()
        with open(args.after, encoding="utf-8") as source:
            after_text = source.read()
    except OSError as error:
        print("check_preservation: %s" % error, file=sys.stderr)
        return 2
    findings = analyze_text(before_text, after_text)
    result = {"before": args.before, "after": args.after, "drift_detected": bool(findings), "findings": findings}
    print(json.dumps(result, indent=2) if args.json else render_human(result))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
