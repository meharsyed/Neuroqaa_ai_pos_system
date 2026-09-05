import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CartItem } from "@/types/sales";

export interface HeldCart {
  id: string;
  name: string;
  items: CartItem[];
  saleDiscountPct: string;
  applyTax: boolean;
  customerPhone: string;
  customerName: string;
  savedAt: number; // timestamp
}

interface HeldCartsState {
  carts: HeldCart[];
  addCart: (name: string, items: CartItem[], saleDiscountPct: string, applyTax: boolean, customerPhone: string, customerName: string) => string;
  deleteCart: (id: string) => void;
  getCart: (id: string) => HeldCart | undefined;
  listCarts: () => HeldCart[];
}

export const useHeldCartsStore = create<HeldCartsState>()(
  persist(
    (set, get) => ({
      carts: [],

      addCart: (name, items, saleDiscountPct, applyTax, customerPhone, customerName) => {
        const id = `cart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newCart: HeldCart = {
          id,
          name,
          items,
          saleDiscountPct,
          applyTax,
          customerPhone,
          customerName,
          savedAt: Date.now(),
        };
        set((state) => ({
          carts: [...state.carts, newCart],
        }));
        return id;
      },

      deleteCart: (id) => {
        set((state) => ({
          carts: state.carts.filter((cart) => cart.id !== id),
        }));
      },

      getCart: (id) => {
        return get().carts.find((cart) => cart.id === id);
      },

      listCarts: () => {
        return get().carts.sort((a, b) => b.savedAt - a.savedAt);
      },
    }),
    {
      name: "held-carts-store",
    }
  )
);