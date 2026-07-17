import CatalogManager from "../components/CatalogManager";
import type { Brand } from "../types";

export default function BrandsPage() {
  return (
    <CatalogManager<Brand>
      kind="brand"
      title="Brands"
      subtitle="Brand master data"
      endpoint="/brands"
      emptyDescription="Add your first brand to organize products and purchase review matches."
    />
  );
}
