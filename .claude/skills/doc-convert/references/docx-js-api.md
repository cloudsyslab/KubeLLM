# docx-js API Reference (Condensed)

Quick reference for the `docx` npm package used by `md_to_docx.js`. Read this when customizing the script or building documents beyond what the script handles.

## Setup
```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, ExternalHyperlink,
  HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign,
  PageNumber, PageBreak, UnderlineType } = require('docx');
```

## Document & Styles
```javascript
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 20 } } }, // 10pt default
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "000000", font: "Times New Roman" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } }
    ]
  },
  sections: [{ properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [/* content */] }]
});
// Size units: half-points (24 = 12pt). Margin units: DXA (1440 = 1 inch).
Packer.toBuffer(doc).then(buf => fs.writeFileSync("out.docx", buf));
```

**Override built-in styles** by using exact IDs: `"Title"`, `"Heading1"`, `"Heading2"`, `"Heading3"`.

## Text & Formatting
```javascript
new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 200, after: 200 },
  children: [
    new TextRun({ text: "Bold", bold: true, font: "Arial", size: 24 }),
    new TextRun({ text: "Italic", italics: true }),
    new TextRun({ text: "Colored", color: "FF0000" }),
    new TextRun({ text: "Underlined", underline: { type: UnderlineType.SINGLE } })
  ]
});
```
**Never use `\n`** for line breaks. Always use separate `Paragraph` elements.

## Headings
```javascript
new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Doc Title")] })
new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Section")] })
new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Subsection")] })
```

## Lists
```javascript
// Define in Document config:
numbering: { config: [
  { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
  { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
] }
// Use in content:
new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun("Item")] })
```
**Use `LevelFormat.BULLET` constant**, not the string `"bullet"`. Same reference = continues numbering; different reference = restarts.

## Tables
```javascript
const border = { style: BorderStyle.SINGLE, size: 1, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };
new Table({
  columnWidths: [4680, 4680], // DXA units. Letter usable width = 9360 (with 1" margins)
  rows: [new TableRow({
    tableHeader: true,
    children: [new TableCell({
      borders, width: { size: 4680, type: WidthType.DXA },
      shading: { fill: "D9E2F3", type: ShadingType.CLEAR }, // ALWAYS use CLEAR, never SOLID
      children: [new Paragraph({ children: [new TextRun({ text: "Header", bold: true })] })]
    })]
  })]
});
```
Set **both** `columnWidths` on Table and `width` on each cell. Apply borders to cells, not the table.

## Hyperlinks
```javascript
new Paragraph({ children: [
  new ExternalHyperlink({
    children: [new TextRun({ text: "Click here", style: "Hyperlink" })],
    link: "https://example.com"
  })
] });
```

## Headers, Footers & Page Numbers
```javascript
sections: [{
  headers: { default: new Header({ children: [new Paragraph({ children: [new TextRun("Header")] })] }) },
  footers: { default: new Footer({ children: [new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT] }), new TextRun(" of "),
      new TextRun({ children: [PageNumber.TOTAL_PAGES] })]
  })] }) },
  children: [/* content */]
}]
```

## Page Breaks
```javascript
new Paragraph({ children: [new PageBreak()] }) // MUST be inside a Paragraph
new Paragraph({ pageBreakBefore: true, children: [new TextRun("New page")] })
```

## Quick Reference
| Unit | Value |
|------|-------|
| Font size | Half-points: 20 = 10pt, 24 = 12pt, 28 = 14pt |
| Margins/widths | DXA: 1440 = 1 inch, 720 = 0.5 inch |
| Letter usable width | 9360 DXA (with 1" margins) |
| Spacing | 240 = single line, 276 = 1.15 line |
