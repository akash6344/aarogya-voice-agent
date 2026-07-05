import { randomUUID } from 'crypto';
import { AccessToken, type VideoGrant } from 'livekit-server-sdk';
import { NextResponse } from 'next/server';
import { STT_PROVIDERS, SUPPORTED_LANGUAGES, type Language, type SttProvider } from '@/lib/config';
import { checkRateLimit } from '@/lib/rate-limit';

function allowedOrigin(request: Request): boolean {
  const allowed = (process.env.ALLOWED_ORIGINS ?? 'http://localhost:3000')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
  const origin = request.headers.get('origin');
  if (!origin) {
    return true;
  }
  return allowed.includes(origin);
}

async function verifyTurnstile(token: unknown, ip: string): Promise<boolean> {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;
  if (!secret || !siteKey) {
    return true;
  }
  if (typeof token !== 'string' || !token) {
    return false;
  }

  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ secret, response: token, remoteip: ip }),
  });
  const data = (await response.json()) as { success?: boolean };
  return Boolean(data.success);
}

export async function POST(request: Request) {
  if (!allowedOrigin(request)) {
    return NextResponse.json({ error: 'Origin not allowed' }, { status: 403 });
  }

  const ip = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? 'unknown';
  const defaultMax = process.env.NODE_ENV === 'development' ? 100 : 10;
  const maxCalls = Number(process.env.MAX_CALLS_PER_IP_PER_HOUR ?? defaultMax);
  if (!checkRateLimit(ip, maxCalls)) {
    return NextResponse.json({ error: 'Rate limit exceeded' }, { status: 429 });
  }

  let body: { language?: unknown; stt?: unknown; turnstileToken?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }

  if (!SUPPORTED_LANGUAGES.includes(body.language as Language)) {
    return NextResponse.json({ error: 'Unsupported language' }, { status: 400 });
  }

  const sttProvider: SttProvider = STT_PROVIDERS.includes(body.stt as SttProvider)
    ? (body.stt as SttProvider)
    : 'deepgram';

  if (!(await verifyTurnstile(body.turnstileToken, ip))) {
    return NextResponse.json({ error: 'Human verification failed' }, { status: 403 });
  }

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const livekitUrl = process.env.LIVEKIT_URL;
  if (!apiKey || !apiSecret || !livekitUrl) {
    return NextResponse.json({ error: 'LiveKit is not configured' }, { status: 500 });
  }

  const roomName = `aarogya-${randomUUID()}`;
  const identity = `patient-${randomUUID()}`;
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canSubscribe: true,
  };

  const token = new AccessToken(apiKey, apiSecret, {
    identity,
    name: 'Patient',
    ttl: '7m',
    metadata: JSON.stringify({ language: body.language, stt: sttProvider }),
  });
  token.addGrant(grant);

  return NextResponse.json({
    serverUrl: livekitUrl,
    roomName,
    participantToken: await token.toJwt(),
  });
}
