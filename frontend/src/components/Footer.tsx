import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="w-full bg-sf-dark text-sf-cream border-t border-sf-cream/20 font-sans">
      {/* Upper editorial block */}
      <div className="w-full max-w-none px-4 md:px-8 py-12 md:py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-8">
          {/* Brand Philosophy */}
          <div className="md:col-span-1 space-y-4">
            <h2 className="font-serif text-3xl tracking-widest text-sf-cream">
              SHOPPERFLOX
            </h2>
            <p className="text-[12px] uppercase tracking-wider text-sf-cream/70 leading-relaxed font-sans">
              SHOPPERFLOX — ОДЕЖДА И АКСЕССУАРЫ. Архитектурный крой, премиальные ткани и внимание к деталям.
            </p>
            <div className="pt-2 text-sf-cream font-serif text-2xl font-light">
              СТИЛЬ В ДЕТАЛЯХ”
            </div>
          </div>

          {/* Navigation links */}
          <div className="space-y-3">
            <div className="text-[12px] font-semibold uppercase tracking-wider text-sf-cream/50">
              ( РАЗДЕЛЫ )
            </div>
            <ul className="space-y-2 text-[13px] uppercase tracking-wider">
              <li>
                <Link to="/" className="hover:text-sf-denim transition-colors">
                  КАТАЛОГ ТОВАРОВ
                </Link>
              </li>
              <li>
                <Link to="/favorites" className="hover:text-sf-denim transition-colors">
                  ИЗБРАННОЕ
                </Link>
              </li>
              <li>
                <Link to="/orders" className="hover:text-sf-denim transition-colors">
                  МОИ ЗАКАЗЫ
                </Link>
              </li>
              <li>
                <Link to="/cart" className="hover:text-sf-denim transition-colors">
                  КОРЗИНА
                </Link>
              </li>
            </ul>
          </div>

          {/* Service & Process */}
          <div className="space-y-3">
            <div className="text-[12px] font-semibold uppercase tracking-wider text-sf-cream/50">
              ( СЕРВИС )
            </div>
            <ul className="space-y-2 text-[13px] uppercase tracking-wider text-sf-cream/90">
              <li>
                <Link to="/" className="hover:text-sf-denim transition-colors">
                  НОВЫЕ ПОСТУПЛЕНИЯ
                </Link>
              </li>
              <li>
                <Link to="/orders" className="hover:text-sf-denim transition-colors">
                  СТАТУС ЗАКАЗА
                </Link>
              </li>
              <li>
                <Link to="/cart" className="hover:text-sf-denim transition-colors">
                  ОФОРМЛЕНИЕ ЗАКАЗА
                </Link>
              </li>
            </ul>
          </div>

          {/* Support & Contacts */}
          <div className="space-y-3">
            <div className="text-[12px] font-semibold uppercase tracking-wider text-sf-cream/50">
              ( ПОДДЕРЖКА )
            </div>
            <div className="text-[12px] text-sf-cream/80 space-y-1">
              <div>СЛУЖБА ЗАБОТЫ:</div>
              <div>
                <a
                  href="mailto:support@shopper.flox"
                  className="font-semibold text-sf-cream hover:underline"
                >
                  support@shopper.flox
                </a>
              </div>
            </div>
            <div className="pt-2 text-[11px] text-sf-cream/60 uppercase">
              ЕЖЕДНЕВНО С 10:00 ДО 21:00
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Legal / Copyright */}
      <div className="border-t border-sf-cream/15 py-6">
        <div className="w-full max-w-none px-4 md:px-8 flex flex-col md:flex-row items-center justify-between gap-4 text-[11px] text-sf-cream/60 uppercase tracking-wider">
          <div>© {new Date().getFullYear()} SHOPPERFLOX. ВСЕ ПРАВА ЗАЩИЩЕНЫ.</div>
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
