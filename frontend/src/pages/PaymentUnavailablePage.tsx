import { Link } from 'react-router-dom';

export function PaymentUnavailablePage() {
  return (
    <div className="w-full bg-[#F2E9DB] min-h-[75vh] flex items-center justify-center py-16 md:py-24 px-4 md:px-8">
      <div className="max-w-3xl w-full mx-auto bg-[#FFFFFF] border border-[#3F2021] p-8 sm:p-14 rounded-none text-center space-y-8">
        <div>
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block mb-3">
            ( ТЕХНИЧЕСКОЕ ОБСЛУЖИВАНИЕ ПЛАТЁЖНОГО ШЛЮЗА )
          </span>

          <h1 className="font-serif text-2xl sm:text-3xl md:text-4xl uppercase tracking-wider text-[#3F2021] leading-relaxed">
            ОПЛАТА ВРЕМЕННО НЕ РАБОТАЕТ, НО МЫ РАБОТАЕМ НАД ЭТИМ, ПРОСИМ ПРОЩЕНИЯ, ВЕРНИТЕСЬ К ОПЛАТЕ ЧЕРЕЗ НЕСКОЛЬКО ЧАСОВ
          </h1>
        </div>

        <div className="w-16 h-px bg-[#3F2021]/30 mx-auto" />

        <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 max-w-lg mx-auto leading-relaxed">
          Ваш заказ сохранён в личном кабинете со статусом «Ожидает оплаты». Вы сможете завершить платёж позже из раздела «Мои заказы», как только платёжная система возобновит штатную работу.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link
            to="/orders"
            className="w-full sm:w-auto bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-8 py-3.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none"
          >
            МОИ ЗАКАЗЫ ↗
          </Link>
          <Link
            to="/catalog"
            className="w-full sm:w-auto border border-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] text-[#3F2021] px-8 py-3.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none"
          >
            ВЕРНУТЬСЯ В КАТАЛОГ ↗
          </Link>
        </div>

        <div className="pt-6 border-t border-[#3F2021]/15 text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
          СЛУЖБА ПОДДЕРЖКИ: support@shopper.flox
        </div>
      </div>
    </div>
  );
}

export default PaymentUnavailablePage;
