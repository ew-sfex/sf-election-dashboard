/**
 * Cloudflare Worker: CORS + 15s Edge Cache Proxy for SF Department of Elections 2026 XML
 * Deploy on a free Cloudflare account and set VITE_ELECTION_DATA_URL to the Worker URL,
 * or rely on the built-in GitHub Actions live feed sync to public/data/summary.xml.
 */
const UPSTREAM_URL = 'https://sfelections.org/results/20261103/data/summary.xml';

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    const upstream = await fetch(UPSTREAM_URL, {
      cf: { cacheTtl: 15, cacheEverything: true },
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        Accept: 'application/xml,text/xml,*/*;q=0.8',
      },
    });

    const body = await upstream.arrayBuffer();
    return new Response(body, {
      status: upstream.status,
      headers: {
        'Content-Type': 'application/xml; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=15, s-maxage=15',
      },
    });
  },
};
