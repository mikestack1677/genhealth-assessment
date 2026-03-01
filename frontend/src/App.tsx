import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout/Layout";
import { ActivityPage } from "./pages/ActivityPage/ActivityPage";
import { OrderDetailPage } from "./pages/OrderDetailPage/OrderDetailPage";
import { OrdersPage } from "./pages/OrdersPage/OrdersPage";
import { QueryProvider } from "./providers/QueryProvider";
import { ThemeProvider } from "./providers/ThemeProvider";
import "./styles/globals.css";

export function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<OrdersPage />} />
              <Route path="/orders/:id" element={<OrderDetailPage />} />
              <Route path="/activity" element={<ActivityPage />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </ThemeProvider>
    </QueryProvider>
  );
}
