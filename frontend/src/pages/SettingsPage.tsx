import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, AlertTriangle, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FormTextField } from "@/components/forms";
import { configApi } from "@/lib/config";
import { useAuthStore } from "@/store/authStore";
import { useToast } from "@/lib/use-toast";
import type { Setting } from "@/types/config";

const GROUPS: { label: string; keys: string[] }[] = [
  { label: "Shop Information", keys: ["shop_name", "shop_address", "shop_phone", "shop_email"] },
  { label: "Receipt", keys: ["receipt_header", "receipt_footer", "receipt_width", "default_receipt_template", "show_serial_numbers_on_receipt"] },
  { label: "Thermal Printer", keys: ["thermal_printer_ip", "thermal_printer_port"] },
  { label: "Sales & Stock", keys: ["tax_pct", "low_stock_threshold", "cashier_return_limit_paise"] },
  {
    label: "Warranty Clause",
    keys: [
      "warranty_note_enabled",
      "warranty_note_language",
      "warranty_note_en",
      "warranty_note_ur",
    ],
  },
];

/** Which language the warranty clause prints in. */
const WARRANTY_LANGUAGES = [
  { value: "en", label: "English only" },
  { value: "ur", label: "Urdu only" },
  { value: "both", label: "Both — English then Urdu" },
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
      <p className="text-[6px] font-bold tracking-wide text-n-700 leading-none mt-0.5">RECEIPT</p>
      <div className="w-8 h-1 bg-n-300 rounded-sm" />
      <div className="w-full border-t border-dashed border-n-300" />
      <div className="w-9 h-1 bg-n-300 rounded-sm" />
      <div className="w-9 h-1 bg-n-300 rounded-sm" />
      <div className="w-9 h-1 bg-n-300 rounded-sm" />
      <div className="w-full border-t border-dashed border-n-300" />
      <p className="text-[6px] font-bold text-n-800 leading-none">Rs. 000</p>
    </div>
  );
}

function InvoicePreview() {
  return (
    <div className="w-20 h-28 bg-white border rounded-sm shadow-md overflow-hidden shrink-0 flex flex-col">
      <div className="h-2 bg-info w-full" />
      <div className="flex items-center gap-1 px-1.5 pt-2">
        <div className="w-3 h-3 rounded-full bg-info shrink-0" />
        <p className="text-[7px] font-bold text-info leading-none tracking-wide">INVOICE</p>
      </div>
      <div className="flex flex-col gap-1 px-1.5 pt-2.5">
        <div className="flex justify-between items-center">
          <div className="w-7 h-1 bg-n-300 rounded-sm" />
          <div className="w-3 h-1 bg-n-300 rounded-sm" />
        </div>
        <div className="flex justify-between items-center">
          <div className="w-6 h-1 bg-n-200 rounded-sm" />
          <div className="w-3 h-1 bg-n-200 rounded-sm" />
        </div>
        <div className="flex justify-between items-center">
          <div className="w-7 h-1 bg-n-300 rounded-sm" />
          <div className="w-3 h-1 bg-n-300 rounded-sm" />
        </div>
      </div>
      <div className="flex-1" />
      <div className="h-2.5 bg-n-800 mx-1.5 mb-2 rounded-sm flex items-center justify-end px-1">
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
        <div className="flex items-start gap-2 rounded-lg bg-destructive-bg border border-destructive/40 px-3 py-2 text-xs text-destructive">
          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>
            No thermal printer IP is configured yet. Printing will fail until you set one in the
            Thermal Printer section below.
          </span>
        </div>
      )}
      {value === "invoice" && (
        <div className="flex items-start gap-2 rounded-lg bg-info-bg border border-info/40 px-3 py-2 text-xs text-info">
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
  const { toast } = useToast();
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
      toast({ title: "Setting saved", description: `${updated.key} updated successfully` });
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
    <PageContainer>
      <PageHeader
        title="Settings"
        subtitle={!canEdit ? "Read-only access — Only owners and managers can change settings" : ""}
      />

      <div className="max-w-2xl space-y-8">

      {!canEdit && (
        <div className="rounded-lg bg-warning-bg border border-warning/40 px-4 py-3 text-sm text-warning">
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
                <div key={setting.key} className="px-4 py-3 space-y-2">
                  {setting.key === "default_receipt_template" ? (
                    <>
                      <label className="text-sm font-medium">{setting.label}</label>
                      <ReceiptTemplateField
                        value={values[setting.key] ?? "thermal"}
                        onChange={(v) => handleChange(setting.key, v)}
                        disabled={!canEdit}
                        thermalConfigured={!!values["thermal_printer_ip"]?.trim()}
                      />
                    </>
                  ) : setting.key === "warranty_note_language" ? (
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">{setting.label}</label>
                      <div className="flex flex-wrap gap-2">
                        {WARRANTY_LANGUAGES.map((opt) => (
                          <button
                            key={opt.value}
                            type="button"
                            disabled={!canEdit}
                            onClick={() => handleChange(setting.key, opt.value)}
                            className={`rounded-lg border-2 px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 ${
                              (values[setting.key] ?? "en") === opt.value
                                ? "border-primary bg-primary/5 text-primary"
                                : "border-border text-muted-foreground hover:border-primary/50"
                            }`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Applies to the A4/A5 invoice and the shared web bill. The 80&nbsp;mm
                        till slip is always English — a thermal printer has no Urdu
                        characters — and prints the clause only when the bill carries
                        serial numbers.
                      </p>
                    </div>
                  ) : setting.key === "warranty_note_ur" ? (
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">{setting.label}</label>
                      <textarea
                        dir="rtl"
                        lang="ur"
                        rows={3}
                        value={values[setting.key] ?? ""}
                        onChange={(e) => handleChange(setting.key, e.target.value)}
                        disabled={!canEdit}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-right text-base leading-loose disabled:opacity-50"
                        style={{ fontFamily: '"Noto Naskh Arabic","Jameel Noori Nastaleeq",serif' }}
                      />
                      <p className="text-xs text-muted-foreground">{setting.description}</p>
                    </div>
                  ) : setting.key === "warranty_note_en" ? (
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">{setting.label}</label>
                      <textarea
                        rows={3}
                        value={values[setting.key] ?? ""}
                        onChange={(e) => handleChange(setting.key, e.target.value)}
                        disabled={!canEdit}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-50"
                      />
                      <p className="text-xs text-muted-foreground">{setting.description}</p>
                    </div>
                  ) : setting.key === "warranty_note_enabled" ||
                      setting.key === "show_serial_numbers_on_receipt" ? (
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={(values[setting.key] ?? "true").toLowerCase() === "true"}
                        onChange={(e) => handleChange(setting.key, e.target.checked ? "true" : "false")}
                        disabled={!canEdit}
                        className="h-4 w-4 rounded border-border"
                      />
                      <div>
                        <p className="text-sm font-medium">{setting.label}</p>
                        <p className="text-xs text-muted-foreground">{setting.description}</p>
                      </div>
                    </label>
                  ) : (
                    <FormTextField
                      label={setting.label}
                      name={setting.key}
                      value={values[setting.key] ?? ""}
                      onChange={(val) => handleChange(setting.key, val)}
                      disabled={!canEdit}
                      hint={setting.description}
                    />
                  )}
                  {saved[setting.key] && (
                    <span className="text-xs text-green-600 font-medium">✓ Saved</span>
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
    </PageContainer>
  );
}