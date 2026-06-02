import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Users, Search, Plus, X, ChevronLeft, ChevronRight,
  Phone, TrendingUp, Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { paiseToRupees } from "@/lib/catalog";
import { customersApi } from "@/lib/customers";
import type { Customer, CustomerGender } from "@/types/customers";
import type { Sale } from "@/types/sales";

// ── Helpers ───────────────────────────────────────────────────────────────────

const GENDER_LABELS: Record<CustomerGender, string> = {
  M: "Male", F: "Female", O: "Other",
};

function GenderBadge({ gender }: { gender: CustomerGender }) {
  const cls: Record<CustomerGender, string> = {
    M: "bg-blue-100 text-blue-700",
    F: "bg-pink-100 text-pink-700",
    O: "bg-muted text-muted-foreground",
  };
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${cls[gender]}`}>
      {GENDER_LABELS[gender]}
    </span>
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-PK", {
    day: "numeric", month: "short", year: "numeric",
  });
}

// ── Customer history modal ────────────────────────────────────────────────────

function CustomerHistoryModal({
  customer,
  onClose,
}: {
  customer: Customer;
  onClose: () => void;
}) {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["customer-sales", customer.id, page],
    queryFn: () => customersApi.salesHistory(customer.id, page),
    staleTime: 30_000,
  });

  const sales: Sale[] = data?.results ?? [];
  const totalPages = data ? Math.ceil(data.count / 10) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-fade-in-scale">

        {/* Header */}
        <div className="sticky top-0 bg-background px-5 py-4 border-b flex items-center gap-3 z-10">
          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">
            {(customer.name || customer.phone || "?")[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold truncate">{customer.display_name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              {customer.phone && (
                <span className="text-xs text-muted-foreground font-mono flex items-center gap-0.5">
                  <Phone className="h-2.5 w-2.5" />{customer.phone}
                </span>
              )}
              <GenderBadge gender={customer.gender} />
            </div>
          </div>
          <div className="text-right shrink-0 mr-2">
            <p className="font-bold text-sm font-mono">{paiseToRupees(customer.total_revenue_paise)}</p>
            <p className="text-xs text-muted-foreground">{customer.total_sales} purchase{customer.total_sales !== 1 ? "s" : ""}</p>
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
            Purchase History
          </h3>

          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : sales.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">No purchases yet.</p>
          ) : (
            <div className="rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 border-b">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Bill #</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Date</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Items</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Total</th>
                    <th className="px-4 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sales.map((sale) => (
                    <tr
                      key={sale.id}
                      className={`hover:bg-muted/20 transition-colors ${
                        sale.status === "voided" ? "opacity-50" : ""
                      }`}
                    >
                      <td className="px-4 py-2.5 font-mono text-xs font-semibold">{sale.sale_number}</td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">{formatDate(sale.created_at)}</td>
                      <td className="px-4 py-2.5 text-right text-xs">{sale.items.length}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-semibold">
                        {paiseToRupees(sale.total_paise)}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <Badge
                          variant={sale.status === "completed" ? "success" : "destructive"}
                          className="text-[10px]"
                        >
                          {sale.status}
                        </Badge>
                      </td>
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
        </div>
      </div>
    </div>
  );
}

// ── Add customer modal ────────────────────────────────────────────────────────

function AddCustomerModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName]     = useState("");
  const [phone, setPhone]   = useState("");
  const [gender, setGender] = useState<CustomerGender>("O");
  const [notes, setNotes]   = useState("");

  const { mutate, isPending, isError } = useMutation({
    mutationFn: () =>
      customersApi.create({
        name: name.trim() || undefined,
        phone: phone.trim() || undefined,
        gender,
        notes: notes.trim() || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["customers"] });
      onClose();
    },
  });

  const canSave = name.trim() || phone.trim();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-md animate-fade-in-scale">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold">Add New Customer</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground p-1 rounded"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Name <span className="normal-case font-normal">(optional)</span>
            </label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Customer name"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Phone Number
            </label>
            <Input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="03001234567"
              type="tel"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Gender
            </label>
            <div className="flex gap-2">
              {(["M", "F", "O"] as CustomerGender[]).map((g) => (
                <button
                  key={g}
                  onClick={() => setGender(g)}
                  className={`flex-1 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
                    gender === g
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border text-muted-foreground hover:border-primary/50"
                  }`}
                >
                  {GENDER_LABELS[g]}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Notes <span className="normal-case font-normal">(optional)</span>
            </label>
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. VIP, contractor, bulk buyer"
            />
          </div>

          {isError && (
            <p className="text-xs text-destructive bg-destructive/10 rounded-lg px-3 py-2">
              Could not save. The phone number may already be registered.
            </p>
          )}
        </div>

        <div className="px-5 pb-5 flex gap-2">
          <Button variant="outline" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button
            className="flex-1"
            onClick={() => mutate()}
            disabled={isPending || !canSave}
          >
            {isPending ? (
              <><Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> Saving…</>
            ) : (
              "Add Customer"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CustomersPage() {
  const [search, setSearch]           = useState("");
  const [page, setPage]               = useState(1);
  const [selected, setSelected]       = useState<Customer | null>(null);
  const [showAdd, setShowAdd]         = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["customers", { search, page }],
    queryFn: () => customersApi.list({ search, page }),
    staleTime: 30_000,
  });

  const customers  = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / 10) || 1;

  return (
    <div className="min-h-full flex flex-col">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Users className="h-5 w-5 text-primary" />
            <div>
              <h1 className="text-xl font-bold">Customers</h1>
              <p className="text-sm text-muted-foreground">
                {totalCount.toLocaleString()} registered customer{totalCount !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <Button size="sm" onClick={() => setShowAdd(true)} className="gap-1.5">
            <Plus className="h-4 w-4" /> Add Customer
          </Button>
        </div>
      </div>

      <div className="flex-1 p-6 space-y-4">

        {/* Search */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name or phone…"
            className="pl-9"
          />
        </div>

        {/* Customer list */}
        {isLoading ? (
          <div className="rounded-xl border p-12 text-center text-sm text-muted-foreground">
            Loading…
          </div>
        ) : customers.length === 0 ? (
          <div className="rounded-xl border p-12 text-center">
            <Users className="h-8 w-8 mx-auto mb-3 opacity-15" />
            <p className="text-sm font-medium text-muted-foreground">
              {search ? "No customers match your search" : "No customers yet"}
            </p>
            {!search && (
              <Button size="sm" className="mt-4 gap-1.5" onClick={() => setShowAdd(true)}>
                <Plus className="h-3.5 w-3.5" /> Add First Customer
              </Button>
            )}
          </div>
        ) : (
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 border-b">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Customer</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Phone</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Gender</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Purchases</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Total Spent</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Joined</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {customers.map((customer) => (
                  <tr
                    key={customer.id}
                    className="hover:bg-muted/25 transition-colors cursor-pointer"
                    onClick={() => setSelected(customer)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">
                          {(customer.name || customer.phone || "?")[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium leading-tight">
                            {customer.name || (
                              <span className="text-muted-foreground italic text-xs">No name</span>
                            )}
                          </p>
                          <p className="text-[10px] text-muted-foreground">ID #{customer.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono">
                      {customer.phone ?? (
                        <span className="text-muted-foreground/30">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <GenderBadge gender={customer.gender} />
                    </td>
                    <td className="px-4 py-3 text-right font-medium">{customer.total_sales}</td>
                    <td className="px-4 py-3 text-right font-mono font-semibold">
                      {paiseToRupees(customer.total_revenue_paise)}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {formatDate(customer.created_at)}
                    </td>
                    <td className="pr-3 text-center">
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelected(customer); }}
                        className="text-muted-foreground hover:text-primary p-1 rounded hover:bg-primary/10 transition-colors"
                        title="View purchase history"
                      >
                        <TrendingUp className="h-4 w-4" />
                      </button>
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

      {selected && (
        <CustomerHistoryModal customer={selected} onClose={() => setSelected(null)} />
      )}
      {showAdd && <AddCustomerModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}