import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { configApi } from "@/lib/config";
import { useAuthStore } from "@/store/authStore";
import type { Setting } from "@/types/config";

const GROUPS: { label: string; keys: string[] }[] = [
  { label: "Shop Information", keys: ["shop_name", "shop_address", "shop_phone", "shop_email"] },
  { label: "Receipt", keys: ["receipt_header", "receipt_footer", "receipt_width"] },
  { label: "Thermal Printer", keys: ["thermal_printer_ip", "thermal_printer_port"] },
  { label: "Sales & Stock", keys: ["tax_pct", "low_stock_threshold"] },
];

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

      {GROUPS.map(({ label, keys }) => {
        const groupSettings = keys.map((k) => settingMap[k]).filter(Boolean);
        const hasChanges = keys.some((k) => dirty[k]);

        return (
          <section key={label} className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">
                {label}
              </h2>
              {canEdit && hasChanges && (
                <Button
                  size="sm"
                  onClick={() => handleSaveGroup(keys)}
                  disabled={isSaving}
                >
                  <Save className="h-3.5 w-3.5 mr-1.5" />
                  Save
                </Button>
              )}
            </div>

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
                  <Input
                    value={values[setting.key] ?? ""}
                    onChange={(e) => handleChange(setting.key, e.target.value)}
                    disabled={!canEdit}
                    className={`text-sm ${dirty[setting.key] ? "border-primary" : ""}`}
                  />
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}