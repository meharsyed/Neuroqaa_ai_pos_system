import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight, FileText, Loader2, Plus, Printer, Search, Trash2, X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DateTime } from "@/components/ui/date-display";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import { catalogApi } from "@/lib/catalog";
import { quotationsApi } from "@/lib/quotations";
import { apiErrorMessage } from "@/lib/users";
import { useToast } from "@/lib/use-toast";
import type { Product } from "@/types/catalog";
import type { Quotation, QuotationStatus } from "@/types/quotations";
import { useTranslation } from "@/lib/useTranslation";

const STATUS_VARIANT: Record<QuotationStatus, string> = {
  draft: "neutral", sent: "info", accepted: "success",
  declined: "danger", expired: "warning",
};

/** A line being typed. Off-catalogue lines have no productId. */
interface Line {
  key: number;
  productId: number | null;
  name: string;
  sku: string;
  description: string;
  qty: string;
  unitPriceRs: string;
}

const rupees = (paise: number) => (paise / 100).toFixed(2);
const toPaise = (rs: string) => Math.max(0, Math.round((parseFloat(rs) || 0) * 100));

// ── Build / revise a quotation ──────────────────────────────────────────────

function QuotationForm({
  open, onClose, existing,
}: { open: boolean; onClose: () => void; existing?: Quotation | null }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { toast } = useToast();
  const nextKey = useMemo(() => ({ current: 1 }), []);

  const [lines, setLines] = useState<Line[]>(() =>
    existing
      ? existing.items.map((i, n) => ({
          key: n + 1, productId: i.product, name: i.name, sku: i.sku,
          description: i.description, qty: String(parseFloat(i.qty)),
          unitPriceRs: rupees(i.unit_price_paise),
        }))
      : []
  );
  const [customerName, setCustomerName] = useState(existing?.customer_name ?? "");
  const [customerPhone, setCustomerPhone] = useState(existing?.customer_phone ?? "");
  const [customerAddress, setCustomerAddress] = useState(existing?.customer_address ?? "");
  const [profileId, setProfileId] = useState<number | null>(existing?.profile ?? null);
  const [discountRs, setDiscountRs] = useState(rupees(existing?.discount_paise ?? 0));
  const [taxPct, setTaxPct] = useState(existing?.tax_pct ?? "");
  const [installRs, setInstallRs] = useState(rupees(existing?.installation_paise ?? 0));
  const [installNote, setInstallNote] = useState(existing?.installation_note ?? "");
  const [validDays, setValidDays] = useState(String(existing?.valid_days ?? 15));
  const [notes, setNotes] = useState(existing?.notes ?? "");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const { data: profiles = [] } = useQuery({
    queryKey: ["business-profiles"],
    queryFn: quotationsApi.profiles.list,
  });

  const { data: found } = useQuery({
    queryKey: ["qt-product-search", search],
    queryFn: () => catalogApi.products.list({ search }),
    enabled: search.trim().length >= 2,
  });

  function addProduct(p: Product) {
    setLines((ls) => [...ls, {
      key: nextKey.current++, productId: p.id, name: p.name, sku: p.sku,
      description: "", qty: "1", unitPriceRs: rupees(p.sell_price_paise),
    }]);
    setSearch("");
  }

  function addBlankLine() {
    setLines((ls) => [...ls, {
      key: nextKey.current++, productId: null, name: "", sku: "",
      description: "", qty: "1", unitPriceRs: "",
    }]);
  }

  const set = (key: number, patch: Partial<Line>) =>
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const subtotal = lines.reduce(
    (sum, l) => sum + Math.round((parseFloat(l.qty) || 0) * toPaise(l.unitPriceRs)), 0
  );
  const discount = toPaise(discountRs);
  const taxable = Math.max(0, subtotal - discount);
  const pct = parseFloat(taxPct) || 0;
  const tax = Math.round((taxable * pct) / 100);
  const install = toPaise(installRs);
  const total = taxable + tax + install;

  const { mutate, isPending } = useMutation({
    mutationFn: () => {
      const payload = {
        items: lines.map((l) => ({
          product_id: l.productId ?? undefined,
          name: l.name.trim(),
          sku: l.sku.trim(),
          description: l.description.trim(),
          qty: l.qty || "1",
          unit_price_paise: toPaise(l.unitPriceRs),
        })),
        profile_id: profileId,
        customer_name: customerName.trim(),
        customer_phone: customerPhone.trim(),
        customer_address: customerAddress.trim(),
        discount_paise: discount,
        tax_pct: taxPct === "" ? null : pct,
        installation_paise: install,
        installation_note: installNote.trim(),
        valid_days: parseInt(validDays, 10) || 15,
        notes,
      };
      return existing
        ? quotationsApi.revise(existing.id, payload)
        : quotationsApi.create(payload);
    },
    onSuccess: (q) => {
      qc.invalidateQueries({ queryKey: ["quotations"] });
      toast({
        title: existing ? `${q.display_number} revised` : `${q.number} created`,
        description: "Print it, or send it on when you are ready.",
      });
      onClose();
    },
    onError: (err) => setError(apiErrorMessage(err, "Could not save the quotation.")),
  });

  const incomplete = lines.some((l) => !l.productId && !l.name.trim());

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-h-[92vh] max-w-4xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {existing ? `Revise ${existing.display_number}` : "New quotation"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          {/* Who it is for */}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Quote for</label>
              <Input value={customerName} onChange={(e) => setCustomerName(e.target.value)}
                     placeholder="Company or person" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Phone</label>
              <Input value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)}
                     placeholder="03XX XXXXXXX" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Letterhead</label>
              <select
                value={profileId ?? ""}
                onChange={(e) => setProfileId(e.target.value ? Number(e.target.value) : null)}
                className="h-10 w-full rounded-md border border-input bg-background px-2 text-sm"
              >
                <option value="">Default</option>
                {profiles.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Address</label>
            <Input value={customerAddress} onChange={(e) => setCustomerAddress(e.target.value)}
                   placeholder="Printed on the quotation" />
          </div>

          {/* Lines */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative min-w-0 flex-1">
                <Search className="absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search stock to add a line (2+ characters)"
                  className="ps-9"
                />
                {!!found?.results.length && search.trim().length >= 2 && (
                  <div className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border bg-popover shadow-lg">
                    {found.results.slice(0, 8).map((p) => (
                      <button
                        key={p.id}
                        onClick={() => addProduct(p)}
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-start text-sm hover:bg-muted"
                      >
                        <span className="min-w-0 truncate">
                          {p.name}
                          <span className="ms-2 font-mono text-xs text-muted-foreground">{p.sku}</span>
                        </span>
                        <span className="shrink-0 tabular-nums">
                          <Money paise={p.sell_price_paise} />
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {/* The line the whole feature exists for. */}
              <Button variant="outline" onClick={addBlankLine}>
                <Plus className="h-4 w-4" /> Item not in stock
              </Button>
            </div>

            {lines.length === 0 ? (
              <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
                Search your stock above, or add an item you do not carry — cabling,
                labour, anything you are arranging for the customer.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 text-start font-medium">{t("quotations.colDescription")}</th>
                      <th className="w-20 px-2 py-2 text-end font-medium">{t("common.qty")}</th>
                      <th className="w-28 px-2 py-2 text-end font-medium">{t("quotations.colRate")}</th>
                      <th className="w-28 px-3 py-2 text-end font-medium">{t("common.amount")}</th>
                      <th className="w-10" />
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {lines.map((l) => {
                      const amount = Math.round((parseFloat(l.qty) || 0) * toPaise(l.unitPriceRs));
                      return (
                        <tr key={l.key}>
                          <td className="px-3 py-2">
                            {l.productId ? (
                              <>
                                <p className="font-medium">{l.name}</p>
                                <p className="font-mono text-xs text-muted-foreground">{l.sku}</p>
                              </>
                            ) : (
                              <Input
                                value={l.name}
                                onChange={(e) => set(l.key, { name: e.target.value })}
                                placeholder="e.g. Cat-6 cable, 90m — supplied and laid"
                                className="h-8"
                                aria-label="Item description"
                              />
                            )}
                          </td>
                          <td className="px-2 py-2">
                            <Input
                              type="number" min={0} step="1" value={l.qty}
                              onChange={(e) => set(l.key, { qty: e.target.value })}
                              className="h-8 text-end font-mono" aria-label="Quantity"
                            />
                          </td>
                          <td className="px-2 py-2">
                            <Input
                              type="number" min={0} step="50" value={l.unitPriceRs}
                              onChange={(e) => set(l.key, { unitPriceRs: e.target.value })}
                              className="h-8 text-end font-mono" placeholder="0.00"
                              aria-label="Unit price"
                            />
                          </td>
                          <td className="px-3 py-2 text-end font-medium tabular-nums">
                            <Money paise={amount} />
                          </td>
                          <td className="px-1 py-2">
                            <Button size="icon" variant="ghost" aria-label="Remove line"
                                    onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))}>
                              <X className="h-4 w-4" />
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Terms and totals */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Valid for (days)
                </label>
                <Input type="number" min={1} value={validDays}
                       onChange={(e) => setValidDays(e.target.value)} className="w-28" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Notes</label>
                <textarea
                  rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                  placeholder="Delivery time, payment terms, anything the customer should read"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="space-y-2 rounded-lg border bg-muted/30 p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Subtotal</span>
                <span className="tabular-nums"><Money paise={subtotal} /></span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Discount</span>
                <Input type="number" min={0} step="100" value={discountRs}
                       onChange={(e) => setDiscountRs(e.target.value)}
                       className="h-8 w-28 text-end font-mono" aria-label="Discount" />
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Tax %</span>
                <Input type="number" min={0} max={100} step="0.5" value={taxPct}
                       onChange={(e) => setTaxPct(e.target.value)} placeholder="0"
                       className="h-8 w-28 text-end font-mono" aria-label="Tax rate" />
              </div>
              {tax > 0 && (
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Tax amount</span>
                  <span className="tabular-nums"><Money paise={tax} /></span>
                </div>
              )}
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Installation</span>
                <Input type="number" min={0} step="500" value={installRs}
                       onChange={(e) => setInstallRs(e.target.value)}
                       className="h-8 w-28 text-end font-mono" aria-label="Installation" />
              </div>
              {install > 0 && (
                <Input value={installNote} onChange={(e) => setInstallNote(e.target.value)}
                       placeholder="What the labour covers" className="h-8 text-xs" />
              )}
              <div className="flex items-center justify-between border-t pt-2 text-base font-bold">
                <span>Total</span>
                <span className="tabular-nums"><Money paise={total} /></span>
              </div>
            </div>
          </div>

          {error && (
            <p className="whitespace-pre-line rounded-lg border border-destructive/40 bg-destructive-bg px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={onClose} disabled={isPending}>
              Cancel
            </Button>
            <Button
              className="flex-1"
              disabled={isPending || lines.length === 0 || incomplete}
              onClick={() => { setError(""); mutate(); }}
            >
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              {existing ? "Save revision" : "Create quotation"}
            </Button>
          </div>
          {incomplete && (
            <p className="text-xs text-warning">
              One of the lines still needs a description.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── The page ────────────────────────────────────────────────────────────────

export default function QuotationsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [revising, setRevising] = useState<Quotation | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["quotations", search],
    queryFn: () => quotationsApi.list({ search: search || undefined }),
  });

  const { mutate: setStatus } = useMutation({
    mutationFn: ({ id, status }: { id: number; status: QuotationStatus }) =>
      quotationsApi.setStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quotations"] }),
    onError: (err) =>
      toast({ title: apiErrorMessage(err, "Could not update it."), variant: "error" }),
  });

  /**
   * Hand a quotation to the till.
   *
   * Off-catalogue lines cannot deduct stock, so they are called out rather
   * than silently dropped — the cashier has to add them as manual lines.
   */
  const { mutate: sendToTill, isPending: sending } = useMutation({
    mutationFn: (id: number) => quotationsApi.toCart(id),
    onSuccess: (cart) => {
      sessionStorage.setItem("pos.quotationCart", JSON.stringify(cart));
      if (cart.off_catalogue_items.length) {
        toast({
          title: `${cart.off_catalogue_items.length} line(s) are not stock items`,
          description:
            "They cannot be sold from the catalogue — add them at the till by hand.",
        });
      }
      navigate("/checkout");
    },
    onError: (err) =>
      toast({ title: apiErrorMessage(err, "Could not open it at the till."), variant: "error" }),
  });

  const quotations = data?.results ?? [];

  return (
    <PageContainer>
      <PageHeader
        title={t("quotations.title")}
        subtitle={t("quotations.subtitle")}
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" /> {t("quotations.newQuotation")}
          </Button>
        }
      />

      <div className="relative max-w-sm">
        <Search className="absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input value={search} onChange={(e) => setSearch(e.target.value)}
               placeholder={t("quotations.searchPlaceholder")} className="ps-9" />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      ) : quotations.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={t("quotations.noQuotations")}
          description={t("quotations.noQuotationsHint")}
        />
      ) : (
        <div className="divide-y rounded-lg border">
          {quotations.map((q) => (
            <div key={q.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-medium">{q.display_number}</span>
                  <Badge variant={STATUS_VARIANT[q.status] as never}>{q.status}</Badge>
                  {q.is_expired && q.status !== "accepted" && (
                    <Badge variant="warning">{t("quotations.expired")}</Badge>
                  )}
                  {q.converted_sale && <Badge variant="success">{t("quotations.becameSale")}</Badge>}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {q.customer_name || t("quotations.noCustomerNamed")}
                  {" · "}
                  <DateTime value={q.created_at} format="short" />
                  {q.valid_until && ` · ${t("quotations.validTo", { date: q.valid_until })}`}
                  {` · ${q.items.length} line${q.items.length !== 1 ? "s" : ""}`}
                </p>
              </div>

              <span className="shrink-0 font-semibold tabular-nums">
                <Money paise={q.total_paise} />
              </span>

              <Button size="sm" variant="outline" onClick={() => quotationsApi.openPdf(q.id)}>
                <Printer className="h-3.5 w-3.5" /> {t("common.print")}
              </Button>

              {!q.converted_sale && (
                <>
                  <Button size="sm" variant="ghost" onClick={() => setRevising(q)}>
                    {t("quotations.revise")}
                  </Button>
                  {q.status === "draft" && (
                    <Button size="sm" variant="ghost"
                            onClick={() => setStatus({ id: q.id, status: "sent" })}>
                      {t("quotations.markSent")}
                    </Button>
                  )}
                  <Button size="sm" disabled={sending} onClick={() => sendToTill(q.id)}>
                    <ArrowRight className="h-3.5 w-3.5" /> {t("quotations.toTill")}
                  </Button>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      <p className="flex items-start gap-2 rounded-lg border bg-muted/40 px-3 py-2.5 text-xs text-muted-foreground">
        <Trash2 className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          {t("quotations.neverRevenue")}
        </span>
      </p>

      {creating && <QuotationForm open onClose={() => setCreating(false)} />}
      {revising && (
        <QuotationForm open existing={revising} onClose={() => setRevising(null)} />
      )}
    </PageContainer>
  );
}
