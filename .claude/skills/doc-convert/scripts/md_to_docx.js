#!/usr/bin/env node
/**
 * md_to_docx.js - Convert Markdown to professionally formatted Word document
 * Usage: node md_to_docx.js <input.md> <output.docx> [--config styles.json]
 * Requires: npm install -g docx
 */
const fs = require('fs');
const path = require('path');

// Resolve docx module - try local, then global
let docx;
try { docx = require('docx'); } catch {
  const globalDir = process.platform === 'win32'
    ? path.join(process.env.APPDATA || '', 'npm', 'node_modules', 'docx')
    : path.join(process.execPath, '..', '..', 'lib', 'node_modules', 'docx');
  docx = require(globalDir);
}

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, ExternalHyperlink,
  HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign, PageNumber, ThematicBreak } = docx;

// --- Default style config ---
const DEFAULT_STYLE = {
  font: "Times New Roman",
  title: { size: 34, bold: true, centered: true },
  h1: { size: 24, bold: true },
  h2: { size: 20, bold: true },
  h3: { size: 20, bold: true, italic: true },
  body: { size: 20, lineSpacing: 276, afterSpacing: 120 },
  margins: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
  table: { headerFill: "D9E2F3", fontSize: 18, borderColor: "000000" },
  footer: { pageNumbers: true, fontSize: 18 }
};

// --- CLI args ---
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('Usage: node md_to_docx.js <input.md> <output.docx> [--config styles.json]');
  process.exit(1);
}
const inputPath = path.resolve(args[0]);
const outputPath = path.resolve(args[1]);
const configIdx = args.indexOf('--config');
let style = { ...DEFAULT_STYLE };
if (configIdx !== -1 && args[configIdx + 1]) {
  const custom = JSON.parse(fs.readFileSync(path.resolve(args[configIdx + 1]), 'utf-8'));
  style = mergeDeep(style, custom);
}

// --- Helpers ---
function mergeDeep(target, source) {
  const result = { ...target };
  for (const key of Object.keys(source)) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = mergeDeep(target[key] || {}, source[key]);
    } else {
      result[key] = source[key];
    }
  }
  return result;
}

/** Parse inline markdown: **bold**, *italic*, [text](url) into TextRun/Hyperlink array */
function parseInline(text, baseOpts = {}) {
  const runs = [];
  // Regex: **bold**, *italic*, [text](url), or plain text
  const re = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(\[([^\]]+)\]\(([^)]+)\))/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      runs.push(new TextRun({ text: text.slice(last, m.index), font: style.font, ...baseOpts }));
    }
    if (m[1]) { // **bold**
      runs.push(new TextRun({ text: m[2], font: style.font, bold: true, ...baseOpts }));
    } else if (m[3]) { // *italic*
      runs.push(new TextRun({ text: m[4], font: style.font, italics: true, ...baseOpts }));
    } else if (m[5]) { // [text](url)
      runs.push(new ExternalHyperlink({
        children: [new TextRun({ text: m[6], style: "Hyperlink", font: style.font, ...baseOpts })],
        link: m[7]
      }));
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    runs.push(new TextRun({ text: text.slice(last), font: style.font, ...baseOpts }));
  }
  if (runs.length === 0) {
    runs.push(new TextRun({ text, font: style.font, ...baseOpts }));
  }
  return runs;
}

function bodyParagraph(text) {
  return new Paragraph({
    spacing: { after: style.body.afterSpacing, line: style.body.lineSpacing },
    children: parseInline(text, { size: style.body.size })
  });
}

function headingParagraph(text, level) {
  const map = {
    1: { heading: HeadingLevel.TITLE, spacing: { before: 240, after: 400 } },
    2: { heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 } },
    3: { heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 } },
    4: { heading: HeadingLevel.HEADING_3, spacing: { before: 240, after: 120 } }
  };
  const cfg = map[level] || map[4];
  return new Paragraph({
    heading: cfg.heading,
    spacing: cfg.spacing,
    ...(level === 1 ? { alignment: AlignmentType.CENTER } : {}),
    children: parseInline(text, { size: style[level === 1 ? 'title' : level === 2 ? 'h1' : level === 3 ? 'h2' : 'h3'].size })
  });
}

function bulletItem(text) {
  return new Paragraph({
    numbering: { reference: "bullet-list", level: 0 },
    spacing: { after: 60, line: style.body.lineSpacing },
    children: parseInline(text, { size: style.body.size })
  });
}

function numberedItem(text) {
  return new Paragraph({
    numbering: { reference: "numbered-list", level: 0 },
    spacing: { after: 60, line: style.body.lineSpacing },
    children: parseInline(text, { size: style.body.size })
  });
}

// --- Table helpers ---
const tblBorder = () => ({ style: BorderStyle.SINGLE, size: 1, color: style.table.borderColor });
const cellBorders = () => {
  const b = tblBorder();
  return { top: b, bottom: b, left: b, right: b };
};

function buildTable(headerRow, dataRows) {
  const numCols = headerRow.length;
  const usable = 9360; // Letter width minus 1-inch margins in DXA
  const colW = Math.floor(usable / numCols);
  const widths = Array(numCols).fill(colW);

  function makeCell(text, width, isHeader) {
    return new TableCell({
      borders: cellBorders(),
      width: { size: width, type: WidthType.DXA },
      ...(isHeader ? { shading: { fill: style.table.headerFill, type: ShadingType.CLEAR } } : {}),
      verticalAlign: isHeader ? VerticalAlign.CENTER : VerticalAlign.TOP,
      children: [new Paragraph({
        ...(isHeader ? { alignment: AlignmentType.CENTER } : {}),
        spacing: { before: 40, after: 40 },
        children: [new TextRun({
          text, font: style.font, size: style.table.fontSize, ...(isHeader ? { bold: true } : {})
        })]
      })]
    });
  }

  return new Table({
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headerRow.map((t, i) => makeCell(t, widths[i], true))
      }),
      ...dataRows.map(row => new TableRow({
        children: row.map((t, i) => makeCell(t, widths[i], false))
      }))
    ]
  });
}

// --- Markdown parser ---
function parseMarkdown(md) {
  const lines = md.split(/\r?\n/);
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Blank line
    if (line.trim() === '') { i++; continue; }

    // Horizontal rule (---, ***, ___)
    if (/^[-*_]{3,}\s*$/.test(line.trim())) {
      if (style.horizontalRule !== false) {
        elements.push(new Paragraph({
          spacing: { before: 120, after: 120 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "AAAAAA" } }
        }));
      }
      i++;
      continue;
    }

    // Heading
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      elements.push(headingParagraph(headingMatch[2].trim(), headingMatch[1].length));
      i++;
      continue;
    }

    // Table (| ... | ... |)
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      // Parse: first line = header, second = separator (skip), rest = data
      const parseRow = (l) => l.split('|').slice(1, -1).map(c => c.trim());
      if (tableLines.length >= 2) {
        const header = parseRow(tableLines[0]);
        const data = tableLines.slice(2).map(parseRow);
        elements.push(buildTable(header, data));
      }
      continue;
    }

    // Bullet list (- item or * item)
    if (/^\s*[-*]\s+/.test(line)) {
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        elements.push(bulletItem(lines[i].replace(/^\s*[-*]\s+/, '')));
        i++;
      }
      continue;
    }

    // Numbered list (1. item)
    if (/^\s*\d+\.\s+/.test(line)) {
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        elements.push(numberedItem(lines[i].replace(/^\s*\d+\.\s+/, '')));
        i++;
      }
      continue;
    }

    // Body paragraph
    elements.push(bodyParagraph(line));
    i++;
  }

  return elements;
}

// --- Build document ---
const md = fs.readFileSync(inputPath, 'utf-8');
const children = parseMarkdown(md);

const doc = new Document({
  styles: {
    default: { document: { run: { font: style.font, size: style.body.size } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: style.title.size, bold: style.title.bold, color: "000000", font: style.font },
        paragraph: { spacing: { before: 240, after: 200 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: style.h1.size, bold: style.h1.bold, color: "000000", font: style.font },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: style.h2.size, bold: style.h2.bold, color: "000000", font: style.font },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: style.h3.size, bold: style.h3.bold, color: "000000", font: style.font,
          ...(style.h3.italic ? { italics: true } : {}) },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 } }
    ]
  },
  numbering: {
    config: [
      { reference: "bullet-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  sections: [{
    properties: {
      page: { margin: style.margins }
    },
    ...(style.footer.pageNumbers ? {
      footers: {
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT], font: style.font, size: style.footer.fontSize })]
        })] })
      }
    } : {}),
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log('Created: ' + outputPath);
}).catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
