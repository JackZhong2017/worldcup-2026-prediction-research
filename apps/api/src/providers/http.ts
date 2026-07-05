export class ProviderHttpError extends Error {
  constructor(
    readonly provider: string,
    readonly status: number,
    readonly responseBody: string,
  ) {
    super(`${provider} request failed with HTTP ${status}`);
  }
}

export async function getJson<T>(
  provider: string,
  url: URL,
  headers: Readonly<Record<string, string>> = {},
): Promise<T> {
  const response = await fetch(url, {
    headers: { accept: 'application/json', 'user-agent': 'sprp-research/0.1', ...headers },
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) {
    throw new ProviderHttpError(provider, response.status, (await response.text()).slice(0, 1_000));
  }
  return response.json() as Promise<T>;
}
