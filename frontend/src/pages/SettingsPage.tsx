import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Settings, AlertTriangle, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { configApi } from "@/lib/config";
import { useAuthStore } from "@/store/authStore";
import type { Setting } from "@/types/config";

const GROUPS: { label: string; keys: string[] }[] = [
  { label: "Shop Information", keys: ["shop_name", "shop_address", "shop_phone", "shop_email"] },
  { label: "Receipt", keys: ["receipt_header", "receipt_footer", "receipt_width", "default_receipt_template"] },
  { label: "Thermal Printer", keys: ["thermal_printer_ip", "thermal_printer_port"] },
  { label: "Sales & Stock", keys: ["tax_pct", "low_stock_threshold"] },
];

// ── Receipt template picker (with mini visual previews) ─────────────────────

function ThermalPreview() {
  return (
    <div
      className="w-14 h-28 bg-white border border-b-0 shadow-sm flex flex-col items-center gap-1.5 p-2 pb-4 shrink-0"
      style={{
        clipPath:
          "polygon(0% 0%, 100% 0%, 100% 94%, 91% 100%, 82% 94%, 73% 100%, 64% 94%, 55% 100%, 46% 94%, 37% 100%, 28% 94%, 19% 100%, 10% 94%, 0% 100%)",
      }}
    >
      <p className="text-[6px] font-bold tracking-wide text-slate-700 leading-none mt-0.5">RECEIPT</p>
      <div className="w-8 h-1 bg-slate-300 rounded-sm" />
      <div className="w-full border-t border-dashed border-slate-300" />
      <div className="w-9 h-1 bg-slate-300 rounded-sm" />
      <div className="w-9 h-1 bg-slate-300 rounded-sm" />
      <div className="w-9 h-1 bg-slate-300 rounded-sm" />
      <div className="w-full border-t border-dashed border-slate-300" />
      <p className="text-[6px] font-bold text-slate-800 leading-none">Rs. 000</p>
    </div>
  );
}

function InvoicePreview() {
  return (
    <div className="w-20 h-28 bg-white border rounded-sm shadow-md overflow-hidden shrink-0 flex flex-col">
      <div className="h-2 bg-indigo-600 w-full" />
      <div className="flex items-center gap-1 px-1.5 pt-2">
        <div className="w-3 h-3 rounded-full bg-indigo-600 shrink-0" />
        <p className="text-[7px] font-bold text-indigo-600 leading-none tracking-wide">INVOICE</p>
      </div>
      <div className="flex flex-col gap-1 px-1.5 pt-2.5">
        <div className="flex justify-between items-center">
          <div className="w-7 h-1 bg-slate-300 rounded-sm" />
          <div className="w-3 h-1 bg-slate-300 rounded-sm" />
        </div>
        <div className="flex justify-between items-center">
          <div className="w-6 h-1 bg-slate-200 rounded-sm" />
          <div className="w-3 h-1 bg-slate-200 rounded-sm" />
        </div>
        <div className="flex justify-between items-center">
          <div className="w-7 h-1 bg-slate-300 rounded-sm" />
          <div className="w-3 h-1 bg-slate-300 rounded-sm" />
        </div>
      </div>
      <div className="flex-1" />
      <div className="h-2.5 bg-slate-800 mx-1.5 mb-2 rounded-sm flex items-center justify-end px-1">
        <div className="w-4 h-0.5 bg-white/70 rounded-sm" />
      </div>
    </div>
  );
}

const TEMPLATE_OPTIONS = [
  {
    value: "thermal",
    name: "Thermal Receipt Printer",
    desc: "Small till-mounted or handheld receipt printer, prints on a narrow paper roll. Needs its network IP set below.",
    Preview: ThermalPreview,
  },
  {
    value: "invoice",
    name: "Regular Printer",
    desc: "Any normal printer connected to this computer or network — inkjet, laser, or PDF. No setup needed here.",
    Preview: InvoicePreview,
  },
] as const;

function ReceiptTemplateField({
  value,
  onChange,
  disabled,
  thermalConfigured,
}: {
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
  thermalConfigured: boolean;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">Which printer do you have at this till?</p>
      <div className="grid grid-cols-2 gap-2">
        {TEMPLATE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-left transition-colors ${
              value === opt.value
                ? "border-primary bg-primary/5 ring-1 ring-primary"
                : "border-border hover:border-primary/40"
            } disabled:opacity-60 disabled:cursor-not-allowed`}
          >
            <opt.Preview />
            <div className="min-w-0">
              <p className="text-xs font-semibold">{opt.name}</p>
              <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">{opt.desc}</p>
            </div>
          </button>
        ))}
      </div>
      {value === "thermal" && !thermalConfigured && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>
            No thermal printer IP is configured yet. Printing will fail until you set one in the
            Thermal Printer section below.
          </span>
        </div>
      )}
      {value === "invoice" && (
        <div className="flex items-start gap-2 rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-blue-800">
          <Printer className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>
            No setup needed. When you print, your computer's own Print dialog opens and shows every
            printer actually connected to it — just pick one, exactly like printing any document.
          </span>
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const canEdit = user?.role === "owner" || user?.role === "manager";

  const { data: settings = [], isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: configApi.settings.list,
  });

  const [values, setValues] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const initial: Record<string, string> = {};
    settings.forEach((s) => (initial[s.key] = s.value));
    setValues(initial);
    setDirty({});
  }, [settings]);

  const { mutate: saveOne, isPending: isSaving } = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      configApi.settings.update(key, value),
    onSuccess: (updated) => {
      qc.setQueryData(["settings"], (prev: Setting[] | undefined) =>
        prev?.map((s) => (s.key === updated.key ? updated : s))
      );
      setDirty((d) => ({ ...d, [updated.key]: false }));
      setSaved((s) => ({ ...s, [updated.key]: true }));
      setTimeout(() => setSaved((s) => ({ ...s, [updated.key]: false })), 2000);
    },
  });

  const handleChange = (key: string, val: string) => {
    setValues((v) => ({ ...v, [key]: val }));
    setDirty((d) => ({ ...d, [key]: true }));
    setSaved((s) => ({ ...s, [key]: false }));
  };

  const handleSaveGroup = (keys: string[]) => {
    keys.filter((k) => dirty[k]).forEach((k) => saveOne({ key: k, value: values[k] ?? "" }));
  };

  const settingMap = Object.fromEntries(settings.map((s) => [s.key, s]));

  if (isLoading) {
    return (
      <div className="p-8 text-muted-foreground text-sm">Loading settings…</div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <div className="flex items-center gap-3">
        <Settings className="h-5 w-5" />
        <h1 className="text-xl font-semibold">Settings</h1>
      </div>

      {!canEdit && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 px-4 py-3 text-sm text-yellow-800">
          You have read-only access. Only owners and managers can change settings.
        </div>
      )}

      {GROUPS.filter(
        ({ label }) => label !== "Thermal Printer" || (values["default_receipt_template"] ?? "thermal") === "thermal"
      ).map(({ label, keys }) => {
        const groupSettings = keys.map((k) => settingMap[k]).filter(Boolean);
        const hasChanges = keys.some((k) => dirty[k]);

        return (
          <section key={label} className="space-y-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">
              {label}
            </h2>

            <div className="rounded-lg border divide-y">
              {groupSettings.map((setting) => (
                <div key={setting.key} className="px-4 py-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">{setting.label}</label>
                    {saved[setting.key] && (
                      <span className="text-xs text-green-600 font-medium">Saved</span>
                    )}
                  </div>
                  {setting.description && (
                    <p className="text-xs text-muted-foreground">{setting.description}</p>
                  )}
                  {setting.key === "default_receipt_template" ? (
                    <ReceiptTemplateField
                      value={values[setting.key] ?? "thermal"}
                      onChange={(v) => handleChange(setting.key, v)}
                      disabled={!canEdit}
                      thermalConfigured={!!values["thermal_printer_ip"]?.trim()}
                    />
                  ) : (
                    <Input
                      value={values[setting.key] ?? ""}
                      onChange={(e) => handleChange(setting.key, e.target.value)}
                      disabled={!canEdit}
                      className={`text-sm ${dirty[setting.key] ? "border-primary" : ""}`}
                    />
                  )}
                </div>
              ))}
            </div>

            {canEdit && hasChanges && (
              <div className="flex justify-end">
                <Button size="sm" onClick={() => handleSaveGroup(keys)} disabled={isSaving}>
                  <Save className="h-3.5 w-3.5 mr-1.5" />
                  Save
                </Button>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}