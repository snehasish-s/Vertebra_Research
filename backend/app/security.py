"""Single-process demo protections; use a shared limiter before scaling workers."""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
import secrets

from fastapi import HTTPException, Request


class RequestLimiter:
    def __init__(self):
        self.windows = defaultdict(deque)
        self.lock = Lock()

    def check(self, key, limit, seconds):
        now = monotonic()
        with self.lock:
            # Bound memory even if many distinct clients visit this demo.
            if len(self.windows) > 5000:
                self.windows = defaultdict(deque, {key: values for key, values in self.windows.items()
                                                   if values and now - values[-1] < 3600})
                if len(self.windows) > 5000:
                    raise HTTPException(429, 'The demo is busy. Please try again later.')
            window = self.windows[key]
            while window and window[0] <= now - seconds:
                window.popleft()
            if len(window) >= limit:
                raise HTTPException(429, 'Too many requests. Please wait and try again.', headers={'Retry-After': str(seconds)})
            window.append(now)


def authorize(request: Request):
    settings = request.app.state.settings
    expected = settings.demo_access_token
    supplied = request.headers.get('Authorization', '').removeprefix('Bearer ')
    if expected and not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, 'Enter the demo access passphrase to open this library.')
    # Do not trust user-provided forwarding headers. A global cap also protects model spend.
    client = request.client.host if request.client else 'unknown'
    limiter = request.app.state.limiter
    limiter.check(('all', client), settings.requests_per_minute, 60)
    if request.url.path == '/api/questions':
        limiter.check(('questions', 'global'), settings.questions_per_minute, 60)
    if request.method == 'POST' and request.url.path == '/api/documents':
        limiter.check(('uploads', 'global'), settings.uploads_per_hour, 3600)


class BodyLimitMiddleware:
    """Count bytes as they arrive, including requests without Content-Length."""
    def __init__(self, app, maximum):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        maximum = self.maximum if scope['path'] == '/api/documents' else 16_384
        try:
            length = int(headers.get(b'content-length', b'0'))
        except ValueError:
            length = maximum + 1
        from starlette.responses import JSONResponse
        if length > maximum:
            return await JSONResponse({'detail': 'Request is too large. Please use a smaller file or question.'}, 413)(scope, receive, send)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            received += len(message.get('body', b''))
            if received > maximum:
                raise HTTPException(413, 'Request is too large. Please use a smaller file or question.')
            return message

        await self.app(scope, limited_receive, send)
