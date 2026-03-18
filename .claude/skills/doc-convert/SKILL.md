---
name: doc-convert
description: "Convert Markdown files into professionally formatted Word documents (.docx). Use when the user asks to convert a .md file to Word, create a Word doc from markdown content, or reformat text content into a professional .docx document. Supports matching a reference document's formatting style or using a built-in professional default."
---

# Markdown to Word Document Conversion

Convert `.md` files into professionally formatted `.docx` documents using `scripts/md_to_docx.js`.

## Dependencies

Requires the `docx` npm package: `npm install -g docx`

## Workflow

### Default Conversion (no reference document)

1. Run the converter script:
   ```bash
   node <skill-path>/scripts/md_to_docx.js <input.md> <output.docx>
   ```
2. Verify the output file was created and spot-check formatting.

Built-in default style: Times New Roman, 17pt title (centered), 12pt H1, 10pt H2/H3/body, 1-inch margins, page numbers in footer, light blue table header shading.

### Reference-Matched Conversion (match an existing .docx style)

When the user provides a reference `.docx` to match:

1. **Extract style info** from the reference document:
   - Unpack the .docx (it's a ZIP): examine `word/styles.xml` for font names, sizes (`w:sz` values in half-points), spacing, and heading definitions.
   - Note key values: font family, title/h1/h2/h3/body sizes, margins, colors.

2. **Create a style config** JSON file:
   ```json
   {
     "font": "Times New Roman",
     "title": { "size": 34, "bold": true, "centered": true },
     "h1": { "size": 24, "bold": true },
     "h2": { "size": 20, "bold": true },
     "h3": { "size": 20, "bold": true, "italic": true },
     "body": { "size": 20, "lineSpacing": 276, "afterSpacing": 120 },
     "margins": { "top": 1440, "right": 1440, "bottom": 1440, "left": 1440 },
     "table": { "headerFill": "D9E2F3", "fontSize": 18, "borderColor": "000000" },
     "footer": { "pageNumbers": true, "fontSize": 18 }
   }
   ```
   Size values are in half-points (20 = 10pt). Margins are in DXA (1440 = 1 inch).

3. **Run with config**:
   ```bash
   node <skill-path>/scripts/md_to_docx.js <input.md> <output.docx> --config styles.json
   ```

## Supported Markdown Elements

| Markdown | Output |
|----------|--------|
| `# Title` | Document title (centered, bold) |
| `## Section` | Heading 1 |
| `### Subsection` | Heading 2 |
| `#### Sub-subsection` | Heading 3 |
| Body paragraphs | Styled body text with spacing |
| `- item` or `* item` | Bullet list |
| `1. item` | Numbered list |
| `\| col \| col \|` | Table with header row shading |
| `[text](url)` | Clickable hyperlink |
| `**bold**` | Bold inline text |
| `*italic*` | Italic inline text |

## Advanced Customization

For document features beyond what the script handles (images, TOC, tracked changes, headers), read [references/docx-js-api.md](references/docx-js-api.md) and modify the script or build a custom generator.
