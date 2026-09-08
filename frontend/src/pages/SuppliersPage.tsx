import { useState } from "react";
import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Truck, Search, Plus, X, ChevronLeft, ChevronRight,
  Phone, Mail, Loader2, Trash2, ArchiveRestore, AlertTriangle, History,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
import { DateTime } from "@/components/ui/date-display";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { FormTextField } from "@/components/forms";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { catalogApi } from "@/lib/catalog";
import { useToast } from "@/lib/use-toast";
import type { Supplier } from "@/types/catalog";
import { useTranslation } from "@/lib/useTranslation";

// ── Purchase history modal ────────────────────────────────────────────────────

function SupplierHistoryModal({
  supplier,
  onClose,
}: {
  supplier: Supplier;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-purchases", supplier.id, page],
    queryFn: () => catalogApi.suppliers.purchaseHistory(supplier.id, page),
    staleTime: 30_000,
  });

  const movements = data?.results ?? [];
  // Matches the API's DEFAULT_PAGINATION page size (config/settings/base.py).
  const totalPages = data ? Math.ceil(data.count / 50) : 0;
  const totalSpentPaise = movements.reduce((sum, m) => sum + (m.cost_price_paise ?? 0) * Math.abs(parseFloat(m.qty_change)), 0);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-fade-in-scale">
        {/* Header */}
        <div className="sticky top-0 bg-background px-5 py-4 border-b flex items-center gap-3 z-10">
          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">
            {supplier.name[0]?.toUpperCase() ?? "?"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold truncate">{supplier.name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              {supplier.phone && (
                <span className="text-xs text-muted-foreground font-mono flex items-center gap-0.5">
                  <Phone className="h-2.5 w-2.5" />{supplier.phone}
                </span>
              )}
              {!supplier.is_active && <Badge variant="neutral">{t("suppliers.inactive")}</Badge>}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground p-1 rounded hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60">
            {t("suppliers.purchaseHistory")}
          </h3>

          {isLoading ? (
            <div className="rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 border-b">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colProduct")}</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.date")}</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.qty")}</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colCostPrice")}</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colReference")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {[...Array(3)].map((_, i) => (
                    <tr key={i}>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-28" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-20" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-10 ml-auto" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-16 ml-auto" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-16" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : movements.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">{t("suppliers.noPurchases")}</p>
          ) : (
            <div className="rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 border-b">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colProduct")}</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.date")}</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.qty")}</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colCostPrice")}</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colReference")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {movements.map((m) => (
                    <tr key={m.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-2.5">
                        <p className="font-medium leading-tight">{m.product_name}</p>
                        <p className="text-[10px] text-muted-foreground font-mono">{m.product_sku}</p>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">
                        <DateTime value={m.created_at} format="short" />
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{m.qty_change}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-semibold">
                        {m.cost_price_paise != null ? <Money paise={m.cost_price_paise} /> : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">{m.reference || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {totalPages > 1 && (
                <div className="px-4 py-2.5 border-t bg-muted/20 flex items-center justify-between">
                  <Button
                    variant="outline" size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
                  <Button
                    variant="outline" size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          )}

          {!isLoading && movements.length > 0 && page === 1 && totalPages <= 1 && (
            <div className="flex justify-end pt-1">
              <p className="text-xs text-muted-foreground">
                {t("common.total")}: <Money paise={totalSpentPaise} className="font-semibold text-foreground" />
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Add/edit supplier modal ───────────────────────────────────────────────────

function SupplierModal({
  supplier,
  onClose,
}: {
  supplier: Supplier | null;
  onClose: () => void;
}) {
  const isEdit = Boolean(supplier);
  const qc = useQueryClient();
  const { toast } = useToast();
  const { t } = useTranslation();

  const [name, setName] = useState(supplier?.name ?? "");
  const [contactPerson, setContactPerson] = useState(supplier?.contact_person ?? "");
  const [phone, setPhone] = useState(supplier?.phone ?? "");
  const [email, setEmail] = useState(supplier?.email ?? "");
  const [address, setAddress] = useState(supplier?.address ?? "");
  const [notes, setNotes] = useState(supplier?.notes ?? "");

  const { mutate, isPending, isError } = useMutation({
    mutationFn: () => {
      const payload = {
        name: name.trim(),
        contact_person: contactPerson.trim(),
        phone: phone.trim(),
        email: email.trim(),
        address: address.trim(),
        notes: notes.trim(),
      };
      return isEdit
        ? catalogApi.suppliers.update(supplier!.id, payload)
        : catalogApi.suppliers.create(payload);
    },
    onSuccess: (saved) => {
      toast({
        title: isEdit ? "Supplier updated" : "Supplier added",
        description: saved.name,
      });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      onClose();
    },
  });

  const canSave = name.trim().length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto animate-fade-in-scale">
        <div className="sticky top-0 bg-background px-5 py-4 border-b flex items-center justify-between z-10">
          <h2 className="font-semibold">{isEdit ? t("suppliers.editTitle") : t("suppliers.addTitle")}</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground p-1 rounded"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <FormTextField
            label={t("suppliers.fieldName")}
            name="name"
            value={name}
            onChange={setName}
            placeholder="e.g. Al-Karam Traders"
            required
          />

          <FormTextField
            label={t("suppliers.fieldContactPerson")}
            name="contact_person"
            value={contactPerson}
            onChange={setContactPerson}
            placeholder="e.g. Imran Bhai"
            hint="Optional"
          />

          <FormTextField
            label={t("suppliers.fieldPhone")}
            name="phone"
            value={phone}
            onChange={setPhone}
            placeholder="03001234567"
            type="tel"
            hint="Optional"
          />

          <FormTextField
            label={t("suppliers.fieldEmail")}
            name="email"
            value={email}
            onChange={setEmail}
            placeholder="supplier@example.com"
            type="email"
            hint="Optional"
          />

          <FormTextField
            label={t("suppliers.fieldAddress")}
            name="address"
            value={address}
            onChange={setAddress}
            placeholder="Shop / warehouse address"
            hint="Optional"
          />

          <FormTextField
            label={t("suppliers.fieldNotes")}
            name="notes"
            value={notes}
            onChange={setNotes}
            placeholder="e.g. Best for CCTV cameras, usually 2-day lead time"
            hint="Optional - for your reference"
          />

          {isError && (
            <p className="text-xs text-destructive bg-destructive/10 rounded-lg px-3 py-2">
              Could not save. Please check the details and try again.
            </p>
          )}
        </div>

        <div className="px-5 pb-5 flex gap-2">
          <Button variant="outline" className="flex-1" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            className="flex-1"
            onClick={() => mutate()}
            disabled={isPending || !canSave}
          >
            {isPending ? (
              <><Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> {t("common.saving")}</>
            ) : isEdit ? (
              t("common.save")
            ) : (
              t("suppliers.newSupplier")
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Remove/deactivate confirm dialog ──────────────────────────────────────────

function RemoveSupplierDialog({
  supplier,
  onClose,
}: {
  supplier: Supplier | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const { t } = useTranslation();

  const { mutate, isPending } = useMutation({
    mutationFn: () => catalogApi.suppliers.remove(supplier!.id),
    onSuccess: (result) => {
      toast({
        title: result.archived ? t("suppliers.deactivatedToast") : t("suppliers.deletedToast"),
        description: result.detail,
      });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      onClose();
    },
  });

  return (
    <Dialog open={!!supplier} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t("suppliers.removeConfirmTitle")}</DialogTitle>
        </DialogHeader>

        {supplier && (
          <div className="space-y-4">
            <p className="text-sm font-medium">{supplier.name}</p>
            <p className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning-bg px-3 py-2.5 text-sm text-warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                {t("suppliers.removeConfirmDeleteBody")}{" "}{t("suppliers.removeConfirmDeactivateBody")}
              </span>
            </p>
          </div>
        )}

        <div className="flex gap-2 pt-2">
          <Button variant="outline" className="flex-1" onClick={onClose} disabled={isPending}>
            {t("common.cancel")}
          </Button>
          <Button variant="destructive" className="flex-1" onClick={() => mutate()} disabled={isPending}>
            {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t("suppliers.deactivate")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SuppliersPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [historyFor, setHistoryFor] = useState<Supplier | null>(null);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [removing, setRemoving] = useState<Supplier | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", { search, page }],
    queryFn: () => catalogApi.suppliers.list({ search, page }),
    staleTime: 30_000,
  });

  const restoreMutation = useMutation({
    mutationFn: (id: number) => catalogApi.suppliers.restore(id),
    onSuccess: (supplier) => {
      toast({ title: t("suppliers.reactivatedToast"), description: supplier.name });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
  });

  const suppliers = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  // Matches the API's DEFAULT_PAGINATION page size (config/settings/base.py),
  // not a guessed page length.
  const totalPages = Math.ceil(totalCount / 50) || 1;

  return (
    <PageContainer>
      <PageHeader
        title={t("suppliers.title")}
        subtitle={t("suppliers.subtitle", { count: totalCount.toLocaleString() })}
        actions={
          <Button size="sm" onClick={() => setShowAdd(true)} className="gap-1.5">
            <Plus className="h-4 w-4" /> {t("suppliers.newSupplier")}
          </Button>
        }
      />

      <div className="space-y-4">
        {/* Search */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder={t("suppliers.searchPlaceholder")}
            className="pl-9"
          />
        </div>

        {/* Supplier list */}
        {isLoading ? (
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 border-b">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.name")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colContact")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.phone")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colStatus")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colAdded")}</th>
                  <th className="w-32" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {[...Array(5)].map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                    <td className="pr-3"><Skeleton className="h-4 w-16 mx-auto" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : suppliers.length === 0 ? (
          <EmptyState
            icon={Truck}
            title={search ? t("suppliers.noSuppliersSearchTitle") : t("suppliers.noSuppliersTitle")}
            description={search ? t("suppliers.noSuppliersSearchDescription") : t("suppliers.noSuppliersDescription")}
            action={!search ? (
              <Button size="sm" onClick={() => setShowAdd(true)} className="gap-1.5">
                <Plus className="h-4 w-4" /> {t("suppliers.addFirstSupplier")}
              </Button>
            ) : undefined}
          />
        ) : (
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 border-b">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.name")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colContact")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("common.phone")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colStatus")}</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("suppliers.colAdded")}</th>
                  <th className="w-32" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {suppliers.map((supplier) => (
                  <tr
                    key={supplier.id}
                    className="hover:bg-muted/25 transition-colors cursor-pointer"
                    onClick={() => setHistoryFor(supplier)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">
                          {supplier.name[0]?.toUpperCase() ?? "?"}
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium leading-tight truncate max-w-[180px]" title={supplier.name}>
                            {supplier.name}
                          </p>
                          {supplier.email && (
                            <p className="text-[10px] text-muted-foreground flex items-center gap-0.5 truncate max-w-[180px]">
                              <Mail className="h-2.5 w-2.5 shrink-0" />{supplier.email}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {supplier.contact_person || <span className="text-muted-foreground/30">—</span>}
                    </td>
                    <td className="px-4 py-3 text-xs font-mono">
                      {supplier.phone ? (
                        <span className="flex items-center gap-1">
                          <Phone className="h-3 w-3 text-muted-foreground" />{supplier.phone}
                        </span>
                      ) : (
                        <span className="text-muted-foreground/30">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={supplier.is_active ? "success" : "neutral"} className="text-[10px]">
                        {supplier.is_active ? t("suppliers.active") : t("suppliers.inactive")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      <DateTime value={supplier.created_at} format="short" />
                    </td>
                    <td className="pr-3" onClick={(e) => e.stopPropagation()}>
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost" size="icon"
                          onClick={() => setHistoryFor(supplier)}
                          title={t("suppliers.viewHistory")}
                        >
                          <History className="h-4 w-4 text-muted-foreground" />
                        </Button>
                        <Button
                          variant="ghost" size="sm"
                          onClick={() => setEditing(supplier)}
                        >
                          {t("common.edit")}
                        </Button>
                        {supplier.is_active ? (
                          <Button
                            variant="ghost" size="icon"
                            onClick={() => setRemoving(supplier)}
                            title={t("suppliers.deactivate")}
                            aria-label={`Remove ${supplier.name}`}
                          >
                            <Trash2 className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        ) : (
                          <Button
                            variant="ghost" size="icon"
                            onClick={() => restoreMutation.mutate(supplier.id)}
                            title={t("suppliers.reactivate")}
                          >
                            <ArchiveRestore className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="px-4 py-3 border-t bg-muted/20 flex items-center justify-between">
                <Button
                  variant="outline" size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="gap-1"
                >
                  <ChevronLeft className="h-4 w-4" /> Prev
                </Button>
                <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
                <Button
                  variant="outline" size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="gap-1"
                >
                  Next <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {historyFor && (
        <SupplierHistoryModal supplier={historyFor} onClose={() => setHistoryFor(null)} />
      )}
      {(showAdd || editing) && (
        <SupplierModal
          supplier={editing}
          onClose={() => { setShowAdd(false); setEditing(null); }}
        />
      )}
      <RemoveSupplierDialog supplier={removing} onClose={() => setRemoving(null)} />
    </PageContainer>
  );
}
