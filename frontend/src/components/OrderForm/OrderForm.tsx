import { type FormEvent, useState } from "react";
import type { Order, OrderCreate, OrderStatus } from "../../api/types";
import styles from "./OrderForm.module.css";

interface OrderFormProps {
  order?: Order;
  onSubmit: (data: OrderCreate) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

export function OrderForm({ order, onSubmit, onCancel, isSubmitting }: OrderFormProps) {
  const [firstName, setFirstName] = useState(order?.patient_first_name ?? "");
  const [lastName, setLastName] = useState(order?.patient_last_name ?? "");
  const [dob, setDob] = useState(order?.patient_dob ?? "");
  const [status, setStatus] = useState<OrderStatus>(order?.status ?? "pending");
  const [notes, setNotes] = useState(order?.notes ?? "");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const data: OrderCreate = {
      patient_first_name: firstName || undefined,
      patient_last_name: lastName || undefined,
      patient_dob: dob || undefined,
      status,
      notes: notes || undefined,
    };
    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className={styles.form} aria-label="Order form">
      <h2 className={styles.title}>{order ? "Edit Order" : "New Order"}</h2>

      <div className={styles.field}>
        <label htmlFor="firstName" className={styles.label}>
          First Name
        </label>
        <input
          id="firstName"
          type="text"
          className={styles.input}
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          placeholder="First name"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="lastName" className={styles.label}>
          Last Name
        </label>
        <input
          id="lastName"
          type="text"
          className={styles.input}
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          placeholder="Last name"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="dob" className={styles.label}>
          Date of Birth
        </label>
        <input
          id="dob"
          type="date"
          className={styles.input}
          value={dob}
          onChange={(e) => setDob(e.target.value)}
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="status" className={styles.label}>
          Status
        </label>
        <select
          id="status"
          className={styles.select}
          value={status}
          onChange={(e) => setStatus(e.target.value as OrderStatus)}
        >
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      <div className={styles.field}>
        <label htmlFor="notes" className={styles.label}>
          Notes
        </label>
        <textarea
          id="notes"
          className={styles.textarea}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Additional notes"
          rows={3}
        />
      </div>

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.cancelButton}
          onClick={onCancel}
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : order ? "Update Order" : "Create Order"}
        </button>
      </div>
    </form>
  );
}
