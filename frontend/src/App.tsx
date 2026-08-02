import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import ProtectedRoute from "./routes/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import SalesDashboardPage from "./pages/SalesDashboardPage";
import SalesHistoryPage from "./pages/SalesHistoryPage";
import NewSalePage from "./pages/NewSalePage";
import EditSalePage from "./pages/EditSalePage";
import ProductsPage from "./pages/ProductsPage";
import CategoriesPage from "./pages/CategoriesPage";
import PurchasesPage from "./pages/PurchasesPage";
import PurchaseDetailPage from "./pages/PurchaseDetailPage";
import StockPage from "./pages/StockPage";
import StockAdjustmentPage from "./pages/StockAdjustmentPage";
import StockScanPage from "./pages/StockScanPage";
import SecuritySettingsPage from "./pages/SecuritySettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<SalesDashboardPage />} />
          <Route path="/sales" element={<NewSalePage />} />
          <Route path="/sales/history" element={<SalesHistoryPage />} />
          <Route path="/sales/:saleId/edit" element={<EditSalePage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/categories-brands" element={<CategoriesPage />} />
          <Route path="/brands" element={<Navigate to="/categories" replace />} />
          <Route path="/purchases" element={<PurchasesPage />} />
          <Route path="/purchases/:purchaseId" element={<PurchaseDetailPage />} />
          <Route path="/stock" element={<StockPage />} />
          <Route path="/stock/scan" element={<StockScanPage />} />
          <Route path="/stock/adjustment" element={<StockAdjustmentPage />} />
          <Route path="/stock-adjustment" element={<StockAdjustmentPage />} />
          <Route path="/stock-adjustments" element={<StockAdjustmentPage />} />
          <Route path="/settings/security" element={<SecuritySettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
