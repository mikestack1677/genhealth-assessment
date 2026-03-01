import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getOrder, updateOrder } from "../../api/orders";
import type { OrderCreate } from "../../api/types";
import { OrderForm } from "../../components/OrderForm/OrderForm";
import { UploadCard } from "../../components/UploadCard/UploadCard";
import styles from "./OrderDetailPage.module.css";

const ORDER_KEY = "order";

function formatValue(value: string | null): string {
  return value ?? "—";
}

export function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);

  const {
    data: order,
    isLoading,
    error,
  } = useQuery({
    queryKey: [ORDER_KEY, id],
    queryFn: () => getOrder(id ?? ""),
    enabled: Boolean(id),
  });

  const updateMutation = useMutation({
    mutationFn: (formData: OrderCreate) => updateOrder(id ?? "", formData),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [ORDER_KEY, id] });
      setIsEditing(false);
    },
  });

  if (isLoading) {
    return <div className={styles.loading}>Loading...</div>;
  }

  if (error || !order) {
    return (
      <div className={styles.error} role="alert">
        {error instanceof Error ? error.message : "Order not found."}
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Link to="/" className={styles.backLink}>
        ← Back to Orders
      </Link>

      <div className={styles.header}>
        <h1 className={styles.title}>Order Detail</h1>
        {!isEditing && (
          <button type="button" className={styles.editButton} onClick={() => setIsEditing(true)}>
            Edit
          </button>
        )}
      </div>

      {isEditing ? (
        <OrderForm
          order={order}
          onSubmit={(data) => updateMutation.mutate(data)}
          onCancel={() => setIsEditing(false)}
          isSubmitting={updateMutation.isPending}
        />
      ) : (
        <div className={styles.details}>
          <dl className={styles.dataList}>
            <dt>Order ID</dt>
            <dd>{order.id}</dd>
            <dt>First Name</dt>
            <dd>{formatValue(order.patient_first_name)}</dd>
            <dt>Last Name</dt>
            <dd>{formatValue(order.patient_last_name)}</dd>
            <dt>Date of Birth</dt>
            <dd>{formatValue(order.patient_dob)}</dd>
            <dt>Status</dt>
            <dd>
              <span className={`${styles.badge} ${styles[order.status]}`}>{order.status}</span>
            </dd>
            <dt>Notes</dt>
            <dd>{formatValue(order.notes)}</dd>
            <dt>Document</dt>
            <dd>{formatValue(order.document_filename)}</dd>
            <dt>Created</dt>
            <dd>{new Date(order.created_at).toLocaleString()}</dd>
            <dt>Updated</dt>
            <dd>{new Date(order.updated_at).toLocaleString()}</dd>
          </dl>

          {order.extracted_data && (
            <section className={styles.extractedSection} aria-label="Extracted data">
              <h2 className={styles.sectionTitle}>Extracted Data</h2>
              <pre className={styles.extractedJson}>
                {JSON.stringify(order.extracted_data, null, 2)}
              </pre>
            </section>
          )}
        </div>
      )}

      <div className={styles.uploadSection}>
        <h2 className={styles.sectionTitle}>Upload Document</h2>
        <UploadCard
          orderId={order.id}
          onSuccess={() => {
            void queryClient.invalidateQueries({ queryKey: [ORDER_KEY, id] });
          }}
        />
      </div>
    </div>
  );
}
