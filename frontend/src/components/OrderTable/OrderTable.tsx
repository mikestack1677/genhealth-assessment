import type { Order, OrderStatus } from "../../api/types";
import styles from "./OrderTable.module.css";

interface OrderTableProps {
  orders: Order[];
  onEdit: (order: Order) => void;
  onDelete: (id: string) => void;
  isLoading: boolean;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString();
}

function getPatientName(order: Order): string {
  const first = order.patient_first_name ?? "";
  const last = order.patient_last_name ?? "";
  const name = [first, last].filter(Boolean).join(" ");
  return name || "—";
}

function statusBadgeClass(status: OrderStatus): string {
  switch (status) {
    case "pending":
      return styles.badgeGray;
    case "processing":
      return styles.badgeAmber;
    case "completed":
      return styles.badgeGreen;
  }
}

function SkeletonRow() {
  return (
    <tr className={styles.skeletonRow} data-testid="skeleton-row">
      {[1, 2, 3, 4, 5].map((i) => (
        <td key={i}>
          <div className={styles.skeleton} />
        </td>
      ))}
    </tr>
  );
}

export function OrderTable({ orders, onEdit, onDelete, isLoading }: OrderTableProps) {
  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Patient Name</th>
            <th>DOB</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          )}
          {!isLoading && orders.length === 0 && (
            <tr>
              <td colSpan={5} className={styles.emptyState}>
                No orders found.
              </td>
            </tr>
          )}
          {!isLoading &&
            orders.map((order) => (
              <tr key={order.id}>
                <td>{getPatientName(order)}</td>
                <td>{formatDate(order.patient_dob)}</td>
                <td>
                  <span className={`${styles.badge} ${statusBadgeClass(order.status)}`}>
                    {order.status}
                  </span>
                </td>
                <td>{formatDate(order.created_at)}</td>
                <td className={styles.actions}>
                  <button
                    type="button"
                    className={styles.editButton}
                    onClick={() => onEdit(order)}
                    aria-label={`Edit order ${order.id}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className={styles.deleteButton}
                    onClick={() => onDelete(order.id)}
                    aria-label={`Delete order ${order.id}`}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
