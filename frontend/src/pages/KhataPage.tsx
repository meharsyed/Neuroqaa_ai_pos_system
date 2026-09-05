import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Wallet, Clock, AlertCircle, TrendingUp, Plus, Loader2, User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { customersApi } from "@/lib/customers";
import { useToast } from "@/lib/use-toast";
import type { Customer } from "@/types/customers";

export default function KhataPage() {
  const qc = useQueryClient();
  const { toast } = useToast();

  const [paymentOpen, setPaymentOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentNotes, setPaymentNotes] = useState("");

  const { data: report, isLoading, isError, refetch } = useQuery({
    queryKey: ["khata-report"],
    queryFn: customersApi.khataReport,
    refetchInterval: 30000,
  });

  const { mutate: submitPayment, isPending: isSubmitting } = useMutation({
    mutationFn: (data: { customer_id: number; amount_paise: number; notes?: string }) =>
      customersApi.recordPayment(data),
    onSuccess: () => {
      toast({ title: "Payment recorded", variant: "success" });
      qc.invalidateQueries({ queryKey: ["khata-report"] });
      setPaymentAmount("");
      setPaymentNotes("");
      setPaymentOpen(false);
      setSelectedCustomer(null);
    },
    onError: (err: any) => {
      toast({
        title: "Payment failed",
        description: err.response?.data?.detail || "Unknown error",
        variant: "error",
      });
    },
  });

  const handleRecordPayment = () => {
    if (!selectedCustomer || !paymentAmount) return;

    const amountPaise = Math.round(parseFloat(paymentAmount) * 100);
    if (amountPaise <= 0 || amountPaise > selectedCustomer.outstanding_paise) {
      toast({
        title: "Invalid amount",
        description: "Amount must be between Rs 0.01 and outstanding balance",
        variant: "error",
      });
      return;
    }

    submitPayment({
      customer_id: selectedCustomer.id,
      amount_paise: amountPaise,
      notes: paymentNotes,
    });
  };

  if (isLoading) {
    return (
      <PageContainer>
        <PageHeader
          title="Khata / Customer Credit"
          subtitle="Manage outstanding customer balances"
        />
        <div className="flex items-center justify-center p-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </PageContainer>
    );
  }

  // A failed request must never render as "all customers are paid up" —
  // on a receivables screen that reports the exact opposite of the truth.
  if (isError || !report) {
    return (
      <PageContainer>
        <PageHeader
          title="Khata / Customer Credit"
          subtitle="Manage outstanding customer balances"
        />
        <EmptyState
          icon={AlertCircle}
          title="Could not load the khata report"
          description="The balances could not be fetched, so nothing is shown here. This does not mean customers have no outstanding balance."
          action={<Button onClick={() => refetch()}>Retry</Button>}
        />
      </PageContainer>
    );
  }

  if (report.current.length === 0 && report.days_30.length === 0 && report.days_60.length === 0 && report.days_90_plus.length === 0) {
    return (
      <PageContainer>
        <PageHeader
          title="Khata / Customer Credit"
          subtitle="Manage outstanding customer balances"
        />
        <EmptyState
          icon={Wallet}
          title="No outstanding balances"
          description="All customers are paid up!"
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Khata / Customer Credit"
        subtitle="Manage outstanding customer balances and aging report"
      />

      <div className="max-w-6xl space-y-6">

        {/* Summary Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-lg border bg-card p-4 space-y-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <TrendingUp className="h-4 w-4" />
              Total Outstanding
            </div>
            <p className="text-2xl font-bold">
              <Money paise={report.total_outstanding_paise} />
            </p>
          </div>

          <div className="rounded-lg border bg-card p-4 space-y-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <User className="h-4 w-4" />
              Customers on Credit
            </div>
            <p className="text-2xl font-bold">
              {report.current.length + report.days_30.length + report.days_60.length + report.days_90_plus.length}
            </p>
          </div>

          <div className="rounded-lg border bg-card p-4 space-y-1">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <AlertCircle className="h-4 w-4 text-red-500" />
              90+ Days Overdue
            </div>
            <p className="text-2xl font-bold text-red-600">
              {report.days_90_plus.length}
            </p>
          </div>
        </div>

        {/* Current/Due Soon */}
        {report.current.length > 0 && (
          <div className="rounded-lg border overflow-hidden">
            <div className="px-5 py-3 bg-green-50 border-b flex items-center gap-2">
              <Clock className="h-4 w-4 text-green-600" />
              <h2 className="font-semibold text-sm">Current (Due Soon)</h2>
            </div>
            <div className="divide-y">
              {report.current.map((customer) => (
                <CustomerCreditRow
                  key={customer.id}
                  customer={customer}
                  onPayment={() => {
                    setSelectedCustomer(customer);
                    setPaymentOpen(true);
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* 30 Days Overdue */}
        {report.days_30.length > 0 && (
          <div className="rounded-lg border overflow-hidden">
            <div className="px-5 py-3 bg-yellow-50 border-b flex items-center gap-2">
              <Clock className="h-4 w-4 text-yellow-600" />
              <h2 className="font-semibold text-sm">30+ Days Overdue</h2>
            </div>
            <div className="divide-y">
              {report.days_30.map((customer) => (
                <CustomerCreditRow
                  key={customer.id}
                  customer={customer}
                  onPayment={() => {
                    setSelectedCustomer(customer);
                    setPaymentOpen(true);
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* 60 Days Overdue */}
        {report.days_60.length > 0 && (
          <div className="rounded-lg border overflow-hidden">
            <div className="px-5 py-3 bg-orange-50 border-b flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-orange-600" />
              <h2 className="font-semibold text-sm">60+ Days Overdue</h2>
            </div>
            <div className="divide-y">
              {report.days_60.map((customer) => (
                <CustomerCreditRow
                  key={customer.id}
                  customer={customer}
                  onPayment={() => {
                    setSelectedCustomer(customer);
                    setPaymentOpen(true);
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* 90+ Days Overdue */}
        {report.days_90_plus.length > 0 && (
          <div className="rounded-lg border overflow-hidden">
            <div className="px-5 py-3 bg-red-50 border-b flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <h2 className="font-semibold text-sm">90+ Days Overdue (URGENT)</h2>
            </div>
            <div className="divide-y">
              {report.days_90_plus.map((customer) => (
                <CustomerCreditRow
                  key={customer.id}
                  customer={customer}
                  onPayment={() => {
                    setSelectedCustomer(customer);
                    setPaymentOpen(true);
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* Payment Dialog */}
        {paymentOpen && selectedCustomer && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-background rounded-lg shadow-lg w-full max-w-sm p-6 space-y-4">
              <h2 className="text-lg font-bold">Record Payment</h2>
              <div className="space-y-1">
                <p className="text-sm font-medium">{selectedCustomer.display_name}</p>
                <p className="text-sm text-muted-foreground">
                  Outstanding: <Money paise={selectedCustomer.outstanding_paise} />
                </p>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1.5">
                    Amount (Rs)
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    placeholder="0.00"
                    className="text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1.5">
                    Notes (optional)
                  </label>
                  <Input
                    value={paymentNotes}
                    onChange={(e) => setPaymentNotes(e.target.value)}
                    placeholder="e.g. Check #123, bank transfer"
                    className="text-sm"
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => {
                    setPaymentOpen(false);
                    setSelectedCustomer(null);
                    setPaymentAmount("");
                    setPaymentNotes("");
                  }}
                  size="sm"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleRecordPayment}
                  disabled={isSubmitting || !paymentAmount}
                  size="sm"
                  className="gap-2"
                >
                  {isSubmitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                  Record Payment
                </Button>
              </div>
            </div>
          </div>
        )}

      </div>
    </PageContainer>
  );
}

function CustomerCreditRow({
  customer,
  onPayment,
}: {
  customer: Customer;
  onPayment: () => void;
}) {
  const overdueDays = customer.days_overdue ?? 0;

  return (
    <div className="px-5 py-4 flex items-center justify-between gap-4 hover:bg-muted/20 transition-colors">
      <div className="min-w-0 flex-1">
        <p className="font-medium text-sm truncate">{customer.display_name}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {overdueDays} {overdueDays === 1 ? 'day' : 'days'} overdue
        </p>
      </div>

      <div className="text-right">
        <p className="font-semibold tabular-nums">
          <Money paise={customer.outstanding_paise} />
        </p>
        {overdueDays >= 90 && (
          <Badge variant="danger" className="mt-1">URGENT</Badge>
        )}
      </div>

      <Button
        onClick={onPayment}
        size="sm"
        variant="outline"
        className="shrink-0"
      >
        Record Payment
      </Button>
    </div>
  );
}