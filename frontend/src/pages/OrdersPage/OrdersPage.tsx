import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createOrder, deleteOrder, listOrders, updateOrder } from "../../api/orders";
import type { ExtractedPatientData, Order, OrderCreate } from "../../api/types";
import { OrderForm } from "../../components/OrderForm/OrderForm";
import { OrderTable } from "../../components/OrderTable/OrderTable";
import { Pagination } from "../../components/Pagination/Pagination";
import { UploadCard } from "../../components/UploadCard/UploadCard";
import styles from "./OrdersPage.module.css";

const ORDERS_KEY = "orders";

export function OrdersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: [ORDERS_KEY, page],
    queryFn: () => listOrders(page, 20),
  });

  const createMutation = useMutation({
    mutationFn: (formData: OrderCreate) => createOrder(formData),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [ORDERS_KEY] });
      setShowForm(false);
      setErrorMessage(null);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data: formData }: { id: string; data: OrderCreate }) =>
      updateOrder(id, formData),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [ORDERS_KEY] });
      setEditingOrder(null);
      setShowForm(false);
      setErrorMessage(null);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteOrder(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [ORDERS_KEY] });
      setErrorMessage(null);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
    },
  });

  function handleNewOrder() {
    setEditingOrder(null);
    setShowForm(true);
  }

  function handleEdit(order: Order) {
    setEditingOrder(order);
    setShowForm(true);
  }

  function handleDelete(id: string) {
    deleteMutation.mutate(id);
  }

  function handleFormSubmit(formData: OrderCreate) {
    if (editingOrder) {
      updateMutation.mutate({ id: editingOrder.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  }

  function handleFormCancel() {
    setShowForm(false);
    setEditingOrder(null);
    setErrorMessage(null);
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  const orders = data?.items ?? [];
  const pages = data?.pages ?? 1;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Orders</h1>
        <button type="button" className={styles.newButton} onClick={handleNewOrder}>
          New Order
        </button>
      </div>

      {errorMessage && (
        <div className={styles.error} role="alert">
          {errorMessage}
        </div>
      )}

      <div className={styles.uploadSection}>
        <button
          type="button"
          className={styles.toggleUpload}
          onClick={() => setShowUpload((prev) => !prev)}
          aria-expanded={showUpload}
        >
          {showUpload ? "Hide" : "Extract from PDF"}
        </button>
        {showUpload && (
          <UploadCard
            onSuccess={(result) => {
              if ("first_name" in result) {
                const extracted = result as ExtractedPatientData;
                createMutation.mutate({
                  patient_first_name: extracted.first_name ?? undefined,
                  patient_last_name: extracted.last_name ?? undefined,
                  patient_dob: extracted.date_of_birth ?? undefined,
                  status: "pending",
                });
                setShowUpload(false);
              }
            }}
          />
        )}
      </div>

      {showForm && (
        <div className={styles.formOverlay}>
          <div className={styles.formModal}>
            <OrderForm
              order={editingOrder ?? undefined}
              onSubmit={handleFormSubmit}
              onCancel={handleFormCancel}
              isSubmitting={isSubmitting}
            />
          </div>
        </div>
      )}

      <OrderTable
        orders={orders}
        onEdit={handleEdit}
        onDelete={handleDelete}
        isLoading={isLoading}
      />

      {pages > 1 && <Pagination page={page} pages={pages} onPageChange={setPage} />}
    </div>
  );
}
