import { NextRequest, NextResponse } from 'next/server';
import { extractContent } from '@/lib/extractor';

export const runtime = 'edge'; // Crucial for Cloudflare!

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const targetUrl = searchParams.get('url');

  if (!targetUrl) {
    return NextResponse.json({ error: 'URL is required' }, { status: 400 });
  }

  try {
    const data = await extractContent(targetUrl);
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}