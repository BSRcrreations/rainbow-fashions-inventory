import CatalogManager from "../components/CatalogManager";
import type { Category } from "../types";

export default function CategoriesPage() {
  return (
    <CatalogManager<Category>
      kind="category"
      title="Categories"
      subtitle="Inventory grouping"
      endpoint="/categories"
      emptyDescription="Add your first category to group products for faster search and reporting."
    />
  );
}
