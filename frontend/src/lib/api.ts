const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function createThread(): Promise<{ thread_id: string }> {
  const res = await fetch(`${API_BASE}/api/v1/threads`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to create thread: ${res.status}`);
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(`${API_BASE}/api/v1/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeout);
    return res.ok;
  } catch {
    return false;
  }
}
