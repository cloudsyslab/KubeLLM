---
name: doc-convert
description: >
  Convert Markdown into professionally formatted Word documents. Use when the
  user asks to turn a `.md` file or markdown content into a polished `.docx`,
  optionally matching the style of a reference Word document.
metadata:
  short-description: Convert markdown to Word
---

# Markdown To Word Conversion

Use the bundled `scripts/md_to_docx.js` script for deterministic conversion.

## Default Workflow

1. Confirm the input markdown path and desired output `.docx` path.
2. Ensure the `docx` package is available.
3. Run the converter:

```bash
node scripts/md_to_docx.js <input.md> <output.docx>
```

4. Verify the output file exists and spot-check formatting.

The built-in default style uses:

- Times New Roman
- centered title
- standard 1-inch margins
- page numbers in the footer
- light shading for table headers

## Matching A Reference `.docx`

If the user wants the output to match an existing Word document:

1. Unpack the reference `.docx` as a zip archive.
2. Inspect `word/styles.xml` and related settings files.
3. Extract key values:
   - font family
   - title and heading sizes
   - body size and spacing
   - margin values
   - colors and table styling
4. Create a JSON config file with those values.
5. Run the converter with `--config`:

```bash
node scripts/md_to_docx.js <input.md> <output.docx> --config styles.json
```

## Supported Markdown

The script handles:

- headings
- body paragraphs
- bullet and numbered lists
- tables
- hyperlinks
- inline bold and italic text

For advanced features such as images, headers, TOC, tracked changes, or custom
layout logic, read `references/docx-js-api.md` and then extend the script.

## Notes

- Style sizes in config JSON are half-points.
- Margin values are DXA units.
- Keep the markdown source clean; malformed tables or mixed indentation will
  carry through to the document.
