import { CatalogView } from '../components/CatalogView';

export function CatalogPage() {
  return (
    <div className="w-full bg-[#F2E9DB] min-h-[80vh]">
      <CatalogView eyebrow="( ПОЛНЫЙ КАТАЛОГ )" defaultTitle="ВСЕ ТОВАРЫ" />
    </div>
  );
}
