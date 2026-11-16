import { Link } from 'react-router-dom';
import { CatalogView } from '../components/CatalogView';

export function HomePage() {
  return (
    <div className="w-full">
      {/* 1. HERO SECTION: Full Bleed #3F2021 (Dark Chocolate) */}
      <section
        id="hero-section"
        className="relative w-full bg-sf-dark text-sf-cream overflow-hidden"
      >
        <div className="w-full px-4 md:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[340px] lg:min-h-[420px]">
            {/* Left Column: Editorial Typography */}
            <div className="flex flex-col justify-between py-10 lg:py-14 pr-0 lg:pr-12">
              <div className="space-y-4">
                <div className="text-[11px] sm:text-[12px] font-sans font-medium uppercase tracking-widest text-sf-cream/80">
                  SHOPPERFLOX — ОДЕЖДА И АКСЕССУАРЫ
                </div>

                <div className="relative">
                  <h1 className="font-serif text-4xl sm:text-6xl lg:text-7xl font-normal uppercase leading-[0.95] tracking-tight text-sf-cream">
                    СТИЛЬ
                    <br />
                    В ДЕТАЛЯХ
                  </h1>
                  <span className="font-serif text-6xl sm:text-8xl text-sf-denim/60 leading-none select-none">
                    ”
                  </span>
                </div>

                <p className="max-w-md text-xs sm:text-sm font-sans uppercase tracking-wider text-sf-cream/70 leading-relaxed">
                  Коллекции одежды и аксессуаров вне времени. Бескомпромиссная геометрия, премиальные ткани и архитектурный силуэт.
                </p>
              </div>

              <div className="pt-6 space-y-4">
                <div>
                  <Link
                    to="/catalog"
                    className="inline-block bg-sf-cream text-sf-dark hover:bg-sf-cream/90 px-7 py-3 text-xs font-sans font-semibold uppercase tracking-widest transition-colors"
                  >
                    ПЕРЕЙТИ В КАТАЛОГ ↗
                  </Link>
                </div>

                {/* Internal Navigation Shortcuts */}
                <div className="flex items-center gap-6 text-xs font-semibold uppercase tracking-wider text-sf-denim pt-1">
                  <Link
                    to="/catalog"
                    className="hover:text-sf-cream transition-colors"
                  >
                    КОЛЛЕКЦИИ ↗
                  </Link>
                  <Link
                    to="/favorites"
                    className="hover:text-sf-cream transition-colors"
                  >
                    ИЗБРАННОЕ ↗
                  </Link>
                  <Link
                    to="/cart"
                    className="hover:text-sf-cream transition-colors"
                  >
                    КОРЗИНА ↗
                  </Link>
                </div>
              </div>
            </div>

            {/* Right Column: Editorial Hero Visual */}
            <div className="relative w-full h-full min-h-[300px] lg:min-h-full flex items-center justify-center p-4 lg:p-8 border-t lg:border-t-0 lg:border-l border-sf-cream/20">
              <div className="relative w-full max-w-sm aspect-[2/3] bg-sf-cream/10 border border-sf-cream/30 overflow-hidden flex flex-col justify-between p-5">
                <div className="flex justify-between items-start text-[11px] font-sans tracking-widest text-sf-cream/60">
                  <span>LOOKBOOK // 2026</span>
                  <span>( SHOPPERFLOX )</span>
                </div>

                <div className="text-center space-y-2">
                  <div className="font-serif text-2xl sm:text-3xl uppercase tracking-wider text-sf-cream">
                    АРХИТЕКТУРНЫЙ СИЛУЭТ
                  </div>
                  <div className="text-[10px] sm:text-[11px] font-sans uppercase tracking-widest text-sf-denim">
                    ПРЕМИАЛЬНЫЕ МАТЕРИАЛЫ &amp; ЧЁТКИЕ ЛИНИИ
                  </div>
                </div>

                <div className="flex justify-between items-end text-[11px] font-sans tracking-widest text-sf-cream/60">
                  <span>01 / 08</span>
                  <Link
                    to="/catalog"
                    className="text-sf-cream hover:underline uppercase text-[10px]"
                  >
                    СМОТРЕТЬ КАТАЛОГ ↗
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. FULL CATALOG SECTION: Directly below Hero */}
      <CatalogView
        eyebrow="( КАТАЛОГ SHOPPERFLOX )"
        defaultTitle="ВСЕ ТОВАРЫ"
        className="border-b border-sf-dark/15"
      />

      {/* 3. PHILOSOPHY / PROCESS SECTION: Muted Denim (#7594B3) */}
      <section className="w-full bg-sf-denim text-sf-cream py-16 md:py-24">
        <div className="w-full px-4 md:px-8">
          <div className="max-w-2xl mb-12">
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-cream/70">
              ( ТОТ САМЫЙ АКЦЕНТ )
            </span>
            <h2 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-cream mt-2">
              ТОТ САМЫЙ АКЦЕНТ
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 divide-y md:divide-y-0 md:divide-x divide-sf-cream/30">
            <div className="pt-6 md:pt-0 md:pr-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-sf-cream">
                (1) АНАЛИЗИРУЕМ ТРЕНДЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-sf-cream/85 leading-relaxed">
                Отбираем вневременные силуэты мировых подиумов. Никаких быстротечных микротрендов — только выверенная классика.
              </p>
            </div>

            <div className="pt-6 md:pt-0 md:px-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-sf-cream">
                (2) ВЫБИРАЕМ МАТЕРИАЛЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-sf-cream/85 leading-relaxed">
                Высококачественные премиальные материалы, надежная фурнитура и безупречное качество пошива каждого изделия.
              </p>
            </div>

            <div className="pt-6 md:pt-0 md:pl-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-sf-cream">
                (3) ПРЕМИУМ МАТЕРИАЛЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-sf-cream/85 leading-relaxed">
                Каждое изделие проходит строгий контроль качества материалов, прочности швов и идеальной посадки.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
