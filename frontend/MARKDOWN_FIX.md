# Markdown rendering

Assistant messages are now rendered with `marked` (GitHub-flavored Markdown + line breaks) and sanitized with `DOMPurify` before being assigned through Vue `v-html`.

Supported examples include headings, paragraphs, bold/italic, inline code, fenced code blocks, lists, blockquotes, tables, links, horizontal rules, and images.

Install and run:

```bash
npm install
npm run dev
```
