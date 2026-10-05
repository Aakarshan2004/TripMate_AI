export function extractMcpTexts(content: string): string[] {
  const results: string[] = [];

  // Case 1:
  // [{'type': 'text', 'text': '...', 'id': '...'}]
  const textRegex = /['"]text['"]\s*:\s*(['"])/g;

  let match: RegExpExecArray | null;

  while ((match = textRegex.exec(content)) !== null) {
    const quote = match[1];
    const start = match.index + match[0].length;

    let i = start;
    let escaped = false;

    while (i < content.length) {
      const char = content[i];

      if (escaped) {
        escaped = false;
        i++;
        continue;
      }

      if (char === "\\") {
        escaped = true;
        i++;
        continue;
      }

      if (char === quote) {
        break;
      }

      i++;
    }

    if (i >= content.length) {
      continue;
    }

    const rawText = content.slice(start, i);

    try {
      const decoded = JSON.parse(
        `"${rawText
          .replace(/\\/g, "\\\\")
          .replace(/"/g, '\\"')
          .replace(/\\\\n/g, "\\n")
          .replace(/\\\\t/g, "\\t")}"`
      );

      if (typeof decoded === "string") {
        results.push(decoded);
      }
    } catch {
      results.push(
        rawText
          .replace(/\\n/g, "\n")
          .replace(/\\t/g, "\t")
          .replace(/\\"/g, '"')
          .replace(/\\'/g, "'")
      );
    }

    textRegex.lastIndex = i + 1;
  }

  // Case 2:
  // If content itself is already a JSON string/object.
  if (results.length === 0) {
    try {
      const parsed = JSON.parse(content);

      if (typeof parsed === "string") {
        results.push(parsed);
      }

      if (Array.isArray(parsed)) {
        for (const item of parsed) {
          if (typeof item === "string") {
            results.push(item);
          } else if (
            item &&
            typeof item === "object" &&
            "text" in item &&
            typeof item.text === "string"
          ) {
            results.push(item.text);
          }
        }
      }

      if (
        parsed &&
        typeof parsed === "object" &&
        "text" in parsed &&
        typeof parsed.text === "string"
      ) {
        results.push(parsed.text);
      }
    } catch {
      // Not JSON, continue.
    }
  }

  return [...new Set(results)];
}


export function extractMcpJson<T = unknown>(
  content: string,
): T | null {
  const texts = extractMcpTexts(content);

  // First try every extracted MCP text.
  for (const text of texts) {
    try {
      return JSON.parse(text) as T;
    } catch {
      // Continue searching.
    }
  }

  // Then try the complete content.
  try {
    return JSON.parse(content) as T;
  } catch {
    // Nothing parseable.
  }

  return null;
}