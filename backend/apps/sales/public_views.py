"""
Public, unauthenticated receipt view.

This is the page a customer opens from a WhatsApp link. It is deliberately the
only endpoint in the system that serves sale data without a token, so it is
kept narrow: one signed, expiring link resolves to exactly one bill, and
nothing else is reachable from it.
"""

from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_GET

from .sharing import resolve_receipt_token, sharing_enabled

_GONE_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Receipt unavailable</title>
<style>
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:#F7FAFA;
       font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#1D272C;padding:24px}
  .card{max-width:26rem;text-align:center;background:#fff;border:1px solid #DFE6E8;
        border-radius:12px;padding:32px 28px}
  h1{margin:0 0 8px;font-size:19px;color:#1A3A28}
  p{margin:0;font-size:14px;line-height:1.6;color:#64757D}
</style></head>
<body><div class="card">
  <h1>This receipt link is no longer available</h1>
  <p>The link may have expired, or sharing may have been turned off.
     Please ask the shop for a new copy of your bill.</p>
</div></body></html>"""


@require_GET
@never_cache
@xframe_options_exempt
def public_receipt(request, token: str):
    if not sharing_enabled():
        return HttpResponse(_GONE_PAGE, content_type="text/html; charset=utf-8", status=410)

    sale = resolve_receipt_token(token)
    if sale is None:
        return HttpResponse(_GONE_PAGE, content_type="text/html; charset=utf-8", status=410)

    from apps.config.utils import get_all_settings

    from .receipts import build_receipt_context
    from .receipts import html as receipt_html

    ctx = build_receipt_context(sale, get_all_settings())
    body = receipt_html.render(ctx, format_name="a4")

    resp = HttpResponse(body, content_type="text/html; charset=utf-8")
    # A receipt link is not something to hand to search engines or referrers.
    resp["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    resp["Referrer-Policy"] = "no-referrer"
    return resp
