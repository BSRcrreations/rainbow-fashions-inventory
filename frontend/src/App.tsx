import { lazy, Suspense } from "react";
const QuickEntryPage = lazy(() => import("./pages/QuickEntryPage"));
const ReturnsPage = lazy(() => import("./pages/ReturnsPage"));
const PurchaseReturnsPage = lazy(() => import("./pages/PurchaseReturnsPage"));
const DayClosingPage = lazy(() => import("./pages/DayClosingPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const StoreSettingsPage = lazy(() => import("./pages/StoreSettingsPage"));
const PrinterSettingsPage = lazy(() => import("./pages/PrinterSettingsPage"));
const BackupStatusPage = lazy(() => import("./pages/BackupStatusPage"));
const AuditLogPage = lazy(() => import("./pages/AuditLogPage"));
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import ProtectedRoute from "./routes/ProtectedRoute";
const LoginPage = lazy(() => import("./pages/LoginPage"));
const SalesDashboardPage = lazy(() => import("./pages/SalesDashboardPage"));
const SalesHistoryPage = lazy(() => import("./pages/SalesHistoryPage"));
const NewSalePage = lazy(() => import("./pages/NewSalePage"));
const EditSalePage = lazy(() => import("./pages/EditSalePage"));
const ProductsPage = lazy(() => import("./pages/ProductsPage"));
const CategoriesPage = lazy(() => import("./pages/CategoriesPage"));
const PurchasesPage = lazy(() => import("./pages/PurchasesPage"));
const PurchaseDetailPage = lazy(() => import("./pages/PurchaseDetailPage"));
const SuppliersPage = lazy(() => import("./pages/SuppliersPage"));
const CustomersPage = lazy(() => import("./pages/CustomersPage"));
const ExpensesPage = lazy(() => import("./pages/ExpensesPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const StockPage = lazy(() => import("./pages/StockPage"));
const StockAdjustmentPage = lazy(() => import("./pages/StockAdjustmentPage"));
const StockScanPage = lazy(() => import("./pages/StockScanPage"));
const SecuritySettingsPage = lazy(() => import("./pages/SecuritySettingsPage"));
const OpeningStockImportPage = lazy(() => import("./pages/OpeningStockImportPage"));
const InventoryIntegrityPage = lazy(() => import("./pages/InventoryIntegrityPage"));

export default function App() {
  return (
    <Suspense fallback={<p role="status" className="p-8 text-lg">Loading…</p>}><Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<SalesDashboardPage />} />
          <Route path="/sales" element={<NewSalePage />} />
          <Route path="/stock/quick" element={<QuickEntryPage />} />
          <Route path="/purchases/quick" element={<QuickEntryPage purchase />} />
          <Route path="/purchases/returns" element={<PurchaseReturnsPage />} />
          <Route path="/sales/returns" element={<ReturnsPage />} />
          <Route path="/day-closing" element={<DayClosingPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/store-settings" element={<StoreSettingsPage />} />
          <Route path="/printer-settings" element={<PrinterSettingsPage />} />
          <Route path="/backup-status" element={<BackupStatusPage />} />
          <Route path="/audit-log" element={<AuditLogPage />} />
          <Route path="/sales/history" element={<SalesHistoryPage />} />
          <Route path="/sales/:saleId/edit" element={<EditSalePage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/categories-brands" element={<CategoriesPage />} />
          <Route path="/brands" element={<Navigate to="/categories" replace />} />
          <Route path="/purchases" element={<PurchasesPage />} />
          <Route path="/purchases/:purchaseId" element={<PurchaseDetailPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/expenses" element={<ExpensesPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/stock" element={<StockPage />} />
          <Route path="/stock/scan" element={<StockScanPage />} />
          <Route path="/stock/adjustment" element={<StockAdjustmentPage />} />
          <Route path="/stock/opening-import" element={<OpeningStockImportPage />} />
          <Route path="/stock/integrity" element={<InventoryIntegrityPage />} />
          <Route path="/stock-adjustment" element={<StockAdjustmentPage />} />
          <Route path="/stock-adjustments" element={<StockAdjustmentPage />} />
          <Route path="/settings/security" element={<SecuritySettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></Suspense>
  );
}
