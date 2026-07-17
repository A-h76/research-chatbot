import { marked } from "marked";
import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/core";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import python from "highlight.js/lib/languages/python";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import css from "highlight.js/lib/languages/css";
import sql from "highlight.js/lib/languages/sql";
import katex from "katex";

hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("css", css);
hljs.registerLanguage("sql", sql);

marked.setOptions({ breaks: true, gfm: true });

const MATH_TOKEN = "@@MATHTOKEN";
const CODE_TOKEN = "@@CODETOKEN";

// Protect $...$ / $$...$$ segments from marked/DOMPurify by rendering them
// to KaTeX HTML first, stashing the result, and splicing it back in after
// sanitization (KaTeX's own output is trusted, well-formed markup).
// Code (fenced ``` blocks and inline `code`) is stashed *first* and excluded
// from math substitution, so bash `$HOME` or prices like `$5`/`$10` inside
// code spans don't get misread as math delimiters.
function renderMath(src: string): { text: string; stash: string[] } {
  const stash: string[] = [];
  const pushMath = (html: string) => {
    stash.push(html);
    return `${MATH_TOKEN}${stash.length - 1}@@`;
  };

  const codeStash: string[] = [];
  const pushCode = (raw: string) => {
    codeStash.push(raw);
    return `${CODE_TOKEN}${codeStash.length - 1}@@`;
  };
  let text = src.replace(/```[\s\S]*?```|`[^`\n]*`/g, (m) => pushCode(m));

  const renderDisplay = (expr: string, fallback: string) => {
    try {
      return pushMath(katex.renderToString(expr, { displayMode: true, throwOnError: false }));
    } catch {
      return fallback;
    }
  };
  const renderInline = (expr: string, fallback: string) => {
    try {
      return pushMath(katex.renderToString(expr, { displayMode: false, throwOnError: false }));
    } catch {
      return fallback;
    }
  };

  // Display math: $$...$$ and \[...\]
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, e) => renderDisplay(e, `$$${e}$$`));
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, e) => renderDisplay(e, `\\[${e}\\]`));
  // Inline math: \(...\) and $...$
  text = text.replace(/\\\(([\s\S]+?)\\\)/g, (_, e) => renderInline(e, `\\(${e}\\)`));
  text = text.replace(/(?<!\$)\$(?!\$)([^\n$]+?)\$(?!\$)/g, (_, e) => renderInline(e, `$${e}$`));

  const codeTokenRe = new RegExp(`${CODE_TOKEN}(\\d+)@@`, "g");
  text = text.replace(codeTokenRe, (_, i) => codeStash[Number(i)] ?? "");
  return { text, stash };
}

function restoreMath(html: string, stash: string[]): string {
  const mathTokenRe = new RegExp(`${MATH_TOKEN}(\\d+)@@`, "g");
  return html.replace(mathTokenRe, (_, i) => stash[Number(i)] ?? "");
}

export function renderMarkdown(raw: string): string {
  const { text, stash } = renderMath(raw || "");
  const html = marked.parse(text, { async: false }) as string;
  // KaTeX's visible output is span-based; DOMPurify drops the invisible
  // MathML accessibility tree since those tags aren't in its default
  // profile — an acceptable a11y tradeoff rather than whitelisting ~20 tags.
  const clean = DOMPurify.sanitize(html);
  return restoreMath(clean, stash);
}

export function highlightElement(el: HTMLElement) {
  try {
    hljs.highlightElement(el);
  } catch {
    /* unrecognized language, leave as plain text */
  }
}
