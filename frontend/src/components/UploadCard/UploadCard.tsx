import { type ChangeEvent, type DragEvent, useRef, useState } from "react";
import { extractDocument } from "../../api/documents";
import { uploadDocument } from "../../api/orders";
import type { ExtractedPatientData, Order } from "../../api/types";
import styles from "./UploadCard.module.css";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

interface UploadCardProps {
  orderId?: string;
  onSuccess: (result: ExtractedPatientData | Order) => void;
}

export function UploadCard({ orderId, onSuccess }: UploadCardProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<ExtractedPatientData | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function validateFile(f: File): string | null {
    if (f.type !== "application/pdf") {
      return "Only PDF files are accepted.";
    }
    if (f.size > MAX_FILE_SIZE_BYTES) {
      return "File size must not exceed 10MB.";
    }
    return null;
  }

  function handleFileSelected(f: File) {
    const validationError = validateFile(f);
    if (validationError) {
      setError(validationError);
      setFile(null);
      return;
    }
    setError(null);
    setFile(f);
    setExtractedData(null);
  }

  function handleInputChange(e: ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (selected) {
      handleFileSelected(selected);
    }
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      handleFileSelected(dropped);
    }
  }

  async function handleUpload() {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      if (orderId) {
        const order = await uploadDocument(orderId, file);
        onSuccess(order);
      } else {
        const result = await extractDocument(file);
        setExtractedData(result.extracted);
        onSuccess(result.extracted);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  const buttonLabel = orderId ? "Upload" : "Extract";

  return (
    <div className={styles.card}>
      {/* biome-ignore lint/a11y/noStaticElementInteractions: drag-drop zone; Browse button is the primary accessible interaction */}
      <div
        className={`${styles.dropZone} ${isDragging ? styles.dragging : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        data-testid="upload-zone"
      >
        <p className={styles.dropText}>
          {file ? file.name : "Drag & drop a PDF here, or click to select"}
        </p>
        <button
          type="button"
          className={styles.selectButton}
          onClick={() => fileInputRef.current?.click()}
        >
          Browse
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleInputChange}
          className={styles.hiddenInput}
          aria-label="Select PDF file"
          data-testid="file-input"
        />
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {file && !error && (
        <button
          type="button"
          className={styles.uploadButton}
          onClick={handleUpload}
          disabled={isUploading}
        >
          {isUploading ? "Processing..." : buttonLabel}
        </button>
      )}

      {extractedData && (
        <section className={styles.preview} aria-label="Extracted data">
          <h4 className={styles.previewTitle}>Extracted Patient Data</h4>
          <dl className={styles.dataList}>
            <dt>First Name</dt>
            <dd>{extractedData.first_name ?? "—"}</dd>
            <dt>Last Name</dt>
            <dd>{extractedData.last_name ?? "—"}</dd>
            <dt>Date of Birth</dt>
            <dd>{extractedData.date_of_birth ?? "—"}</dd>
          </dl>
        </section>
      )}
    </div>
  );
}
