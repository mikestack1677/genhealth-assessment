import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { listActivity } from "../../api/activity";
import { ActivityFeed } from "../../components/ActivityFeed/ActivityFeed";
import { Pagination } from "../../components/Pagination/Pagination";
import styles from "./ActivityPage.module.css";

const ACTIVITY_KEY = "activity";

export function ActivityPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: [ACTIVITY_KEY, page],
    queryFn: () => listActivity(page, 20),
    refetchInterval: 30000,
  });

  const logs = data?.items ?? [];
  const pages = data?.pages ?? 1;

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Activity</h1>
      <ActivityFeed logs={logs} isLoading={isLoading} />
      {pages > 1 && <Pagination page={page} pages={pages} onPageChange={setPage} />}
    </div>
  );
}
