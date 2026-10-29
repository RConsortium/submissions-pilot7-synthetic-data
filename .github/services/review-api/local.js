/** Local Node adapter only. Production uses worker.js and durable SQLite. */
import { createServer } from 'node:http';
import { createReviewApi } from './server.js';
const handle = createReviewApi(process.env);
createServer(async (incoming, outgoing) => {
  try {
    const chunks = []; let size = 0;
    for await (const chunk of incoming) {
      size += chunk.length;
      if (size > 24000) { outgoing.writeHead(413); outgoing.end('Review is too large.'); return; }
      chunks.push(chunk);
    }
    const response = await handle(new Request(new URL(incoming.url, process.env.SERVICE_URL), {
      method: incoming.method, headers: incoming.headers,
      ...(['GET', 'HEAD'].includes(incoming.method) ? {} : { body: Buffer.concat(chunks) }),
    }));
    outgoing.writeHead(response.status, Object.fromEntries(response.headers));
    outgoing.end(Buffer.from(await response.arrayBuffer()));
  } catch { outgoing.writeHead(500); outgoing.end('Review service unavailable.'); }
}).listen(Number(process.env.PORT || 8080), '127.0.0.1');
