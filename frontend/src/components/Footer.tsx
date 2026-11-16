import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="w-full bg-amov-dark text-amov-cream border-t border-amov-cream/20 font-sans">
      {/* Upper editorial block */}
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-12 md:py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-8">
          {/* Brand Philosophy */}
          <div className="md:col-span-1 space-y-4">
            <h2 className="font-serif text-3xl tracking-widest text-amov-cream">
              AMÓV
            </h2>
            <p className="text-[12px] uppercase tracking-wider text-amov-cream/70 leading-relaxed font-sans">
              Бренд солнцезащитных очков. Бескомпромиссная геометрия, премиальные материалы и внимание к каждой грани.
            </p>
            <div className="pt-2 text-amov-cream font-serif text-2xl font-light">
              СТИЛЬ В ДЕТАЛЯХ”
            </div>
          </div>

          {/* Navigation links */}
          <div className="space-y-3">
            <div className="text-[12px] font-semibold uppercase tracking-wider text-amov-cream/50">
              ( РАЗДЕЛЫ )
            </div>
            <ul className="space-y-2 text-[13px] uppercase tracking-wider">
              <li>
                <Link to="/" className="hover:text-amov-denim transition-colors">
                  КАТАЛОГ ОЧКОВ
                </Link>
              </li>
              <li>
                <Link to="/favorites" className="hover:text-amov-denim transition-colors">
                  ИЗБРАННОЕ
                </Link>
              </li>
              <li>
                <Link to="/orders" className="hover:text-amov-denim transition-colors">
                  МОИ ЗАКАЗЫ
                </Link>
              </li>
              <li>
                <Link to="/cart" className="hover:text-amov-denim transition-colors">
                  КОРЗИНА
                </Link>
              </li>
            </ul>
          </div>

          {/* Marketplace CTAs */}
          <div className="space-y-3">
            <div className="text-[12px] font-semibold uppercase tracking-wider text-amov-cream/50">
              ( МАРКЕТПЛЕЙСЫ )
            </div>
            <p className="text-[12px] text-amov-cream/70 mb-3">
              Оригинальные коллекции AMÓV с быстрой примеркой:
            </p>
            <div className="flex flex-col space-y-2 font-sans font-semibold text-[13px] uppercase tracking-wider text-amov-denim">
              <a
                href="https://wildberries.ru"
                target="_blank"
                rel="noreferrer"
                className="hover:text-amov-cream transition-colors"
              >
                WILDBERRIES ↗
              </a>
              <a
                href="https://ozon.ru"
                target="_blank"
                rel="noreferrer"
                className="hover:text-amov-cream transition-colors"
              >
                OZON ↗
              </a>
              <a
                href="https://lamoda.ru"
                target="_blank"
                rel="noreferrer"
                className="hover:text-amov-cream transition-colors"
              >
                LAMODA ↗
              </a>
            </div>
          </div>

          {/* Service & Contacts */}
          <div className="space-y-3">
            <div className="text-[12px] font-semibold uppercase tracking-wider text-amov-cream/50">
              ( ПОДДЕРЖКА )
            </div>
            <div className="text-[12px] text-amov-cream/80 space-y-1">
              <div>ЕЖЕДНЕВНО С 10:00 ДО 21:00</div>
              <div className="font-semibold text-amov-cream">CARE@AMOV.SHOP</div>
            </div>
            <div className="pt-2 text-[11px] text-amov-cream/60 uppercase">
              ДОСТАВКА КУРЬЕРОМ ИЛИ В ПУНКТЫ ВЫДАЧИ ПО ВСЕЙ РОССИИ
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Legal / Copyright */}
      <div className="border-t border-amov-cream/15 py-6">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-[11px] text-amov-cream/60 uppercase tracking-wider">
          <div>© {new Date().getFullYear()} AMÓV. ВСЕ ПРАВА ЗАЩИЩЕНЫ.</div>
          <div className="flex gap-6">
            <span>ДОГОВОР ОФЕРТЫ</span>
            <span>ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ</span>
            <span>СЕРТИФИКАТЫ КАЧЕСТВА</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
