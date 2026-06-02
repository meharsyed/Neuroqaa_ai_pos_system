import { apiClient } from "./axios";
import type { Setting } from "@/types/config";

export const configApi = {
  settings: {
    list: () => apiClient.get<Setting[]>("/settings/").then((r) => r.data),
    update: (key: string, value: string) =>
      apiClient.patch<Setting>(`/settings/${key}/`, { value }).then((r) => r.data),
  },
};