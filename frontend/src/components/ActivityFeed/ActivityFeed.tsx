import type { ActivityLog } from "../../api/types";
import styles from "./ActivityFeed.module.css";

interface ActivityFeedProps {
  logs: ActivityLog[];
  isLoading: boolean;
}

function methodBadgeClass(method: string): string {
  switch (method.toUpperCase()) {
    case "GET":
      return styles.methodGet;
    case "POST":
      return styles.methodPost;
    case "PATCH":
    case "PUT":
      return styles.methodPatch;
    case "DELETE":
      return styles.methodDelete;
    default:
      return styles.methodDefault;
  }
}

function statusBadgeClass(code: number): string {
  if (code >= 500) return styles.status5xx;
  if (code >= 400) return styles.status4xx;
  return styles.status2xx;
}

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
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

export function ActivityFeed({ logs, isLoading }: ActivityFeedProps) {
  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Method</th>
            <th>Path</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Time</th>
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
          {!isLoading && logs.length === 0 && (
            <tr>
              <td colSpan={5} className={styles.emptyState}>
                No activity yet.
              </td>
            </tr>
          )}
          {!isLoading &&
            logs.map((log) => (
              <tr key={log.id}>
                <td>
                  <span className={`${styles.badge} ${methodBadgeClass(log.method)}`}>
                    {log.method}
                  </span>
                </td>
                <td className={styles.path}>{log.path}</td>
                <td>
                  <span className={`${styles.badge} ${statusBadgeClass(log.status_code)}`}>
                    {log.status_code}
                  </span>
                </td>
                <td>{log.duration_ms}ms</td>
                <td className={styles.time}>{formatRelativeTime(log.timestamp)}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
