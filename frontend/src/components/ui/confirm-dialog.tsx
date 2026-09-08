import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  placeholder?: string;
  confirmValue?: string;
}

type ConfirmFunction = (options: string | ConfirmOptions) => Promise<boolean>;

const confirmPromises = new Map<string, (value: boolean) => void>();
let confirmId = 0;

interface UseConfirmReturn {
  confirm: ConfirmFunction;
  Dialog: React.ReactNode;
}

export function useConfirm(): UseConfirmReturn {
  const [open, setOpen] = React.useState(false);
  const [options, setOptions] = React.useState<ConfirmOptions | null>(null);
  const [inputValue, setInputValue] = React.useState("");
  const currentId = React.useRef("");

  const confirm: ConfirmFunction = React.useCallback((input) => {
    const opts: ConfirmOptions =
      typeof input === "string"
        ? { title: input }
        : input;

    return new Promise((resolve) => {
      const id = String(confirmId++);
      currentId.current = id;
      confirmPromises.set(id, resolve);
      setOptions(opts);
      setInputValue("");
      setOpen(true);
    });
  }, []);

  const handleConfirm = () => {
    if (options?.confirmValue && inputValue !== options.confirmValue) {
      return;
    }
    const id = currentId.current;
    setOpen(false);
    confirmPromises.get(id)?.(true);
    confirmPromises.delete(id);
  };

  const handleCancel = () => {
    const id = currentId.current;
    setOpen(false);
    confirmPromises.get(id)?.(false);
    confirmPromises.delete(id);
  };

  const isValid = !options?.confirmValue || inputValue === options.confirmValue;

  return {
    confirm,
    Dialog: (
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className={options?.destructive ? "text-destructive" : ""}>
              {options?.title}
            </DialogTitle>
            {options?.description && (
              <DialogDescription>{options.description}</DialogDescription>
            )}
          </DialogHeader>

          {options?.confirmValue && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Type <span className="font-semibold">{options.confirmValue}</span> to confirm
              </p>
              <Input
                placeholder={options.placeholder}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && isValid && handleConfirm()}
                autoFocus
              />
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={handleCancel}>
              {options?.cancelLabel || "Cancel"}
            </Button>
            <Button
              variant={options?.destructive ? "destructive" : "default"}
              onClick={handleConfirm}
              disabled={!isValid}
            >
              {options?.confirmLabel || "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    ),
  };
}