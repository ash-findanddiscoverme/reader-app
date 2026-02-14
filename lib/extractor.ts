import { parseHTML } from 'linkedom';
import { Readability } from '@mozilla/readability';

export async function extractContent(url: string) {
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
    });

    if (!response.ok) throw new Error(`Failed to fetch: ${response.statusText}`);

    const html = await response.text();
    const { document } = parseHTML(html);
    const reader = new Readability(document);
    return reader.parse();
  } catch (error) {
    console.error("Extraction error:", error);
    throw error;
  }
}