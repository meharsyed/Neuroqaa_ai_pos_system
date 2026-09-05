import { useState } from "react";
import { Check, Copy, Loader2, MessageCircle, Share2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { salesApi } from "@/lib/sales";
import { toast } from "@/lib/use-toast";
import type { ShareInfo } from "@/types/sales";

/**
 * Share a bill with the customer.
 *
 * WhatsApp cannot be handed a file from a browser — `wa.me` only carries text —
 * so what actually gets sent is a short summary plus a signed, expiring link to
 * the bill. On a phone or tablet that supports it, the PDF itself is offered
 * through the native share sheet first, which *can* attach to WhatsApp.
 */
export default function ShareReceiptButton({
  saleId,
  saleNumber,
  variant = "outline",
  size = "sm",
  className,
}: {
  saleId: number | string;
  saleNumber?: string;
  variant?: "outline" | "ghost" | "subtle" | "primary";
  size?: "sm" | "md" | "icon";
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [info, setInfo] = useState<ShareInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await salesApi.share(saleId);
      setInfo(data);
      setOpen(true);
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast({
        title: "Could not prepare the share link",
        description: detail ?? "Please try again.",
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  }

  function openWhatsApp() {
    if (!info) return;
    window.open(info.whatsapp_url, "_blank", "noopener");
    setOpen(false);
  }

  async function copyLink() {
    if (!info?.public_url) return;
    try {
      await navigator.clipboard.writeText(info.public_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast({ title: "Could not copy", variant: "error" });
    }
  }

  /**
   * Native share sheet. Only offered when the device can actually share files —
   * that is where WhatsApp can receive the PDF as an attachment rather than a
   * link. Desktop browsers generally cannot, so the button is hidden there.
   */
  const canShareFiles =
    typeof navigator !== "undefined" &&
    typeof navigator.canShare === "function" &&
    typeof navigator.share === "function";

  async function sharePdf() {
    if (!info) return;
    try {
      const blob = await salesApi.receiptPdfBlob(saleId, "invoice");
      const file = new File([blob], `${saleNumber ?? "bill"}.pdf`, { type: "application/pdf" });
      if (!navigator.canShare?.({ files: [file] })) {
        toast({
          title: "This device can't attach files",
          description: "Sending the bill as a link instead.",
        });
        openWhatsApp();
        return;
      }
      await navigator.share({ files: [file], text: info.message });
      setOpen(false);
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return; // user dismissed
      toast({ title: "Could not share the file", description: "Try the link instead." });
    }
  }

  return (
    <>
      <Button variant={variant} size={size} onClick={load} disabled={loading} className={className}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageCircle className="h-4 w-4" />}
        {size !== "icon" && "Share on WhatsApp"}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Share this bill</DialogTitle>
          </DialogHeader>

          {info && (
            <div className="space-y-4">
              {!info.enabled ? (
                <p className="rounded-lg border border-warning/40 bg-warning-bg px-3 py-2.5 text-sm text-warning">
                  Sharing receipts by link is turned off in Settings. The message below
                  will be sent without a link.
                </p>
              ) : !info.public_url ? (
                <p className="rounded-lg border border-warning/40 bg-warning-bg px-3 py-2.5 text-sm text-warning">
                  No public address is configured, so the bill can only be sent as text.
                  Set <span className="font-mono">public_base_url</span> in Settings to
                  include a viewable link.
                </p>
              ) : (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Link to the bill
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="min-w-0 flex-1 truncate rounded-md border bg-muted px-2 py-1.5 text-xs">
                      {info.public_url}
                    </code>
                    <Button size="icon" variant="ghost" onClick={copyLink} title="Copy link">
                      {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Anyone with this link can view this one bill. It stops working after{" "}
                    {info.expires_days} days.
                  </p>
                </div>
              )}

              <div className="space-y-1.5">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Message
                </p>
                <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-md border bg-muted px-3 py-2 text-xs">
                  {info.message}
                </pre>
              </div>

              {!info.customer_phone && (
                <p className="text-xs text-muted-foreground">
                  This sale has no customer number, so WhatsApp will ask you to pick
                  a contact.
                </p>
              )}

              <div className="flex flex-col gap-2 sm:flex-row">
                <Button onClick={openWhatsApp} className="flex-1">
                  <MessageCircle className="h-4 w-4" /> Open WhatsApp
                </Button>
                {canShareFiles && (
                  <Button variant="outline" onClick={sharePdf} className="flex-1">
                    <Share2 className="h-4 w-4" /> Attach the PDF
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
