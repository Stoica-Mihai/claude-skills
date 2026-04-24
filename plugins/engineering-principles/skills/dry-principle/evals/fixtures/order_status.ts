// order/status.ts — existing enum used throughout the codebase.
// Any new code that checks or compares order status MUST import and use
// this type rather than hardcoding raw strings.

export type OrderStatus =
  | "pending"
  | "shipped"
  | "delivered"
  | "cancelled";

export const OrderStatus = {
  Pending: "pending" as const,
  Shipped: "shipped" as const,
  Delivered: "delivered" as const,
  Cancelled: "cancelled" as const,
};

export interface Order {
  id: string;
  status: OrderStatus;
  createdAt: string;
}
