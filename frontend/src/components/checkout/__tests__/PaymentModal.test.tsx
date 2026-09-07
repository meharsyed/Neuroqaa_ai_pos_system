import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PaymentModal from "../PaymentModal";
import type { CartItem, TenderInput } from "@/types/sales";
import type { Customer } from "@/types/customers";

/**
 * The tender arithmetic at the till.
 *
 * This is the one piece of frontend logic that decides how much money changes
 * hands: what settles the bill, what comes back as change, and what is left
 * to go on a customer's khata. The server recomputes all of it, but a till
 * that shows the customer one number and sends another is its own problem.
 */

const CART: CartItem[] = [
  {
    product_id: 1, product_sku: "BUL-4MP-IR", product_name: "4MP IR Bullet",
    product_unit: "pcs", qty: 10, unit_price_paise: 100000,
    discount_pct: 0, discount_paise: 0,
  },
];

const TOTAL = 1000000; // Rs 10,000

function customer(over: Partial<Customer> = {}): Customer {
  return {
    id: 1, name: "Ali", phone: "03001112222", gender: "M", notes: "",
    display_name: "Ali", outstanding_paise: 0, credit_limit_paise: null,
    effective_credit_limit_paise: null, available_credit_paise: null,
    days_overdue: 0, total_sales: 0, total_revenue_paise: 0,
    created_at: new Date().toISOString(), ...over,
  } as Customer;
}

function setup(props: Partial<React.ComponentProps<typeof PaymentModal>> = {}) {
  const onConfirm = vi.fn();
  render(
    <PaymentModal
      cartItems={CART}
      discountPaise={0}
      taxPaise={0}
      totalPaise={TOTAL}
      onConfirm={onConfirm}
      onCancel={vi.fn()}
      isLoading={false}
      {...props}
    />
  );
  return { onConfirm };
}

const amountBox = (label = /cash amount/i) => screen.getByLabelText(label);
const completeButton = () => screen.getByRole("button", { name: /complete sale|rest on khata/i });

beforeEach(() => vi.clearAllMocks());

describe("paying the whole bill", () => {
  it("defaults to the full amount in cash", () => {
    const { onConfirm } = setup();
    fireEvent.click(completeButton());

    expect(onConfirm).toHaveBeenCalledWith<[TenderInput[]]>([
      { method: "cash", amount_paise: TOTAL, amount_tendered_paise: TOTAL },
    ]);
  });

  it("gives change when more cash is handed over than the bill", () => {
    const { onConfirm } = setup();
    fireEvent.change(amountBox(), { target: { value: "12000" } });

    // Rs 12,000 for a Rs 10,000 bill: Rs 10,000 settles it, Rs 2,000 back.
    expect(screen.getByText(/change to give/i)).toBeInTheDocument();
    fireEvent.click(completeButton());
    expect(onConfirm).toHaveBeenCalledWith<[TenderInput[]]>([
      { method: "cash", amount_paise: TOTAL, amount_tendered_paise: 1200000 },
    ]);
  });

  it("never sends more than the bill as the amount settled", () => {
    const { onConfirm } = setup();
    fireEvent.change(amountBox(), { target: { value: "50000" } });
    fireEvent.click(completeButton());

    const [tenders] = onConfirm.mock.calls[0] as [TenderInput[]];
    expect(tenders[0].amount_paise).toBe(TOTAL);
    expect(tenders[0].amount_tendered_paise).toBe(5000000);
  });
});

describe("a part payment", () => {
  it("puts the remainder on the khata when there is a customer", () => {
    const { onConfirm } = setup({ customer: customer() });
    fireEvent.change(amountBox(), { target: { value: "2000" } });

    expect(screen.getByText(/goes on khata/i)).toBeInTheDocument();
    expect(completeButton()).toBeEnabled();

    fireEvent.click(completeButton());
    // Only what was actually taken is sent — the khata part is the server's
    // to work out from the shortfall.
    expect(onConfirm).toHaveBeenCalledWith<[TenderInput[]]>([
      { method: "cash", amount_paise: 200000, amount_tendered_paise: 200000 },
    ]);
  });

  it("is blocked when there is nobody to bill the rest to", () => {
    setup();
    fireEvent.change(amountBox(), { target: { value: "2000" } });

    expect(screen.getByText(/nobody to bill the rest to/i)).toBeInTheDocument();
    expect(completeButton()).toBeDisabled();
  });

  it("relabels the button so nobody part-pays by accident", () => {
    setup({ customer: customer() });
    fireEvent.change(amountBox(), { target: { value: "2000" } });
    expect(screen.getByRole("button", { name: /rest on khata/i })).toBeInTheDocument();
  });
});

describe("the credit limit", () => {
  it("blocks a sale that would break it", () => {
    setup({
      customer: customer({
        effective_credit_limit_paise: 500000,
        available_credit_paise: 500000,
      }),
    });
    // Nothing paid now → the whole Rs 10,000 would go on a Rs 5,000 ceiling.
    fireEvent.change(amountBox(), { target: { value: "0" } });

    expect(screen.getByText(/would break the credit limit/i)).toBeInTheDocument();
    expect(completeButton()).toBeDisabled();
  });

  it("says how much more to collect, rather than just refusing", () => {
    setup({
      customer: customer({
        effective_credit_limit_paise: 500000,
        available_credit_paise: 500000,
      }),
    });
    fireEvent.change(amountBox(), { target: { value: "2000" } });

    // Rs 8,000 would go on a Rs 5,000 ceiling — Rs 3,000 short.
    const banner = screen.getByText(/would break the credit limit/i).closest("div")!;
    expect(within(banner).getByText(/3,000/)).toBeInTheDocument();
  });

  it("lets the sale through once enough has been collected", () => {
    setup({
      customer: customer({
        effective_credit_limit_paise: 500000,
        available_credit_paise: 500000,
      }),
    });
    fireEvent.change(amountBox(), { target: { value: "6000" } });

    expect(screen.queryByText(/would break the credit limit/i)).not.toBeInTheDocument();
    expect(completeButton()).toBeEnabled();
  });

  it("does not block a customer with no limit at all", () => {
    setup({ customer: customer() });
    fireEvent.change(amountBox(), { target: { value: "0" } });
    expect(completeButton()).toBeEnabled();
  });
});

describe("more than one tender", () => {
  it("splits a bill across two methods and settles it in full", () => {
    const { onConfirm } = setup({ customer: customer() });
    fireEvent.change(amountBox(), { target: { value: "4000" } });
    fireEvent.click(screen.getByRole("button", { name: /add another method/i }));

    const boxes = screen.getAllByLabelText(/amount$/i);
    fireEvent.change(boxes[1], { target: { value: "6000" } });

    // Nothing left over, so no khata line.
    expect(screen.queryByText(/goes on khata/i)).not.toBeInTheDocument();
    fireEvent.click(completeButton());

    const [tenders] = onConfirm.mock.calls[0] as [TenderInput[]];
    expect(tenders).toHaveLength(2);
    expect(tenders.reduce((s, t) => s + t.amount_paise, 0)).toBe(TOTAL);
  });

  it("refuses an overpayment, because a card gives no change", () => {
    setup({ customer: customer() });
    fireEvent.click(screen.getByRole("button", { name: /add another method/i }));

    const boxes = screen.getAllByLabelText(/amount$/i);
    fireEvent.change(boxes[1], { target: { value: "5000" } });

    expect(screen.getByText(/more than the bill/i)).toBeInTheDocument();
    expect(completeButton()).toBeDisabled();
  });
});

describe("installation charges", () => {
  it("shows the labour separately and bills the amount due", () => {
    const { onConfirm } = setup({
      installationPaise: 500000,
      totalPaise: TOTAL + 500000,
    });
    expect(screen.getByText(/installation \/ labour/i)).toBeInTheDocument();
    expect(screen.getByText(/amount due/i)).toBeInTheDocument();

    fireEvent.click(completeButton());
    const [tenders] = onConfirm.mock.calls[0] as [TenderInput[]];
    expect(tenders[0].amount_paise).toBe(1500000);
  });
});

describe("a pure khata sale", () => {
  it("sends no tenders at all", () => {
    const { onConfirm } = setup({ customer: customer() });
    fireEvent.click(screen.getByRole("button", { name: /^khata$/i }));

    fireEvent.click(completeButton());
    expect(onConfirm).toHaveBeenCalledWith([]);
  });

  it("is not offered when there is no customer", () => {
    setup();
    expect(screen.queryByRole("button", { name: /^khata$/i })).not.toBeInTheDocument();
  });
});
