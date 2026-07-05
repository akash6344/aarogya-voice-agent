const buckets = new Map<string, { count: number; resetAt: number }>();

export function checkRateLimit(key: string, maxPerHour: number): boolean {
  const now = Date.now();
  const windowMs = 60 * 60 * 1000;
  const entry = buckets.get(key);

  if (!entry || now >= entry.resetAt) {
    buckets.set(key, { count: 1, resetAt: now + windowMs });
    return true;
  }

  if (entry.count >= maxPerHour) {
    return false;
  }

  entry.count += 1;
  return true;
}
