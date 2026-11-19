import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, cartApi, addressesApi, ordersApi, postOfficesApi } from '../api/endpoints';
import { formatPrice } from '../utils/format';
import { formatApiError } from '../utils/errorMapper';
import type { CheckoutRequest, UserAddressResponse, PostOfficeResponse } from '../types/api';
import type { ApiError } from '../api/client';

export function CheckoutPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Queries
  const { data: profileData, isLoading: isProfileLoading } = useQuery({
    queryKey: ['userProfile'],
    queryFn: () => authApi.getMe(),
  });

  const { data: cartData, isLoading: isCartLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: () => cartApi.get(),
  });

  const { data: addressesData } = useQuery({
    queryKey: ['userAddresses'],
    queryFn: () => addressesApi.list(),
  });

  const cart = cartData?.data;
  const items = cart?.items || [];
  const totalAmount = Number(cart?.total_amount || 0);
  const addresses = addressesData?.data || [];
  const personal = profileData?.data?.personal;

  // 1. Recipient Data State
  const [recipientFirstname, setRecipientFirstname] = useState('');
  const [recipientLastname, setRecipientLastname] = useState('');
  const [recipientMiddlename, setRecipientMiddlename] = useState('');
  const [saveToProfile, setSaveToProfile] = useState(false);

  // Auto-fill from user profile
  useEffect(() => {
    if (personal) {
      if (personal.firstname && !recipientFirstname) {
        setRecipientFirstname(personal.firstname);
      }
      if (personal.lastname && !recipientLastname) {
        setRecipientLastname(personal.lastname);
      }
      if (personal.middlename && !recipientMiddlename) {
        setRecipientMiddlename(personal.middlename);
      }
    }
  }, [personal]);

  // 2. Passport Data State
  const [passportSeries, setPassportSeries] = useState('');
  const [passportNumber, setPassportNumber] = useState('');

  // 3. Delivery Mode State
  const [deliveryMode, setDeliveryMode] = useState<'address' | 'post_office'>('address');

  // Address fields
  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(null);
  const [country, setCountry] = useState('Россия');
  const [region, setRegion] = useState('');
  const [city, setCity] = useState('');
  const [house, setHouse] = useState('');
  const [apartment, setApartment] = useState('');
  const [postalCode, setPostalCode] = useState('');
  const [saveAddressToProfile, setSaveAddressToProfile] = useState(false);

  // Auto-select default address if available
  useEffect(() => {
    if (addresses.length > 0 && !selectedAddressId && !city) {
      const defaultAddr = addresses.find((a) => a.is_default) || addresses[0];
      if (defaultAddr) {
        handleSelectSavedAddress(defaultAddr);
      }
    }
  }, [addresses]);

  const handleSelectSavedAddress = (addr: UserAddressResponse) => {
    setSelectedAddressId(addr.id);
    setCountry(addr.country || 'Россия');
    setRegion(addr.region || '');
    setCity(addr.city);
    setHouse(addr.house || addr.street || '');
    setApartment(addr.apartment || '');
    setPostalCode(addr.postal_code);
  };

  // Post office fields
  const [postOfficeSearch, setPostOfficeSearch] = useState('');
  const [selectedPostOfficeId, setSelectedPostOfficeId] = useState<string | null>(null);

  const { data: postOfficesData, isLoading: isPostOfficesLoading } = useQuery({
    queryKey: ['publicPostOffices', postOfficeSearch],
    queryFn: () => postOfficesApi.list({ search: postOfficeSearch.trim() || undefined }),
    enabled: deliveryMode === 'post_office',
  });

  const postOffices = postOfficesData?.data || [];

  // 4. Comment & Error State
  const [comment, setComment] = useState('');
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  // Checkout Mutation
  const checkoutMutation = useMutation({
    mutationFn: (payload: CheckoutRequest) => ordersApi.checkout(payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['profileOrders'] });
      queryClient.invalidateQueries({ queryKey: ['userAddresses'] });
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });

      const checkoutResponse = res.data;
      const paymentMode = checkoutResponse.payment_mode;
      const paymentUrl = checkoutResponse.payment_url;
      const orderId = checkoutResponse.order?.id;

      if (paymentMode === 'billing') {
        if (paymentUrl) {
          window.location.href = paymentUrl;
        } else {
          navigate('/payment-unavailable');
        }
      } else if (paymentMode === 'debug') {
        navigate(`/checkout/pay/${orderId}`);
      } else if (paymentMode === 'unavailable') {
        navigate('/payment-unavailable');
      } else {
        // Fallback checks
        if (paymentUrl) {
          window.location.href = paymentUrl;
        } else {
          navigate('/payment-unavailable');
        }
      }
    },
    onError: (err: ApiError) => {
      setCheckoutError(formatApiError(err, 'ОШИБКА ОФОРМЛЕНИЯ ЗАКАЗА'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCheckoutError(null);

    // Validate recipient
    if (!recipientFirstname.trim() || !recipientLastname.trim()) {
      setCheckoutError('Укажите имя и фамилию получателя');
      return;
    }

    // Validate passport
    const cleanSeries = passportSeries.replace(/\D/g, '');
    const cleanNumber = passportNumber.replace(/\D/g, '');
    if (cleanSeries.length !== 4) {
      setCheckoutError('Серия паспорта должна состоять ровно из 4 цифр');
      return;
    }
    if (cleanNumber.length !== 6) {
      setCheckoutError('Номер паспорта должен состоять ровно из 6 цифр');
      return;
    }

    // Validate delivery
    if (deliveryMode === 'address') {
      if (!city.trim() || !house.trim() || !postalCode.trim()) {
        setCheckoutError('Заполните обязательные поля адреса доставки: Город, Дом, Пост-код');
        return;
      }
    } else {
      if (!selectedPostOfficeId) {
        setCheckoutError('Выберите почтовое отделение для доставки');
        return;
      }
    }

    const payload: CheckoutRequest = {
      recipient_firstname: recipientFirstname.trim(),
      recipient_lastname: recipientLastname.trim(),
      recipient_middlename: recipientMiddlename.trim() || null,
      save_to_profile: saveToProfile,
      passport_series: cleanSeries,
      passport_number: cleanNumber,
      delivery_type: deliveryMode,
      comment: comment.trim() || null,
    };

    if (deliveryMode === 'address') {
      payload.country = country.trim() || 'Россия';
      payload.region = region.trim() || null;
      payload.city = city.trim();
      payload.house = house.trim();
      payload.apartment = apartment.trim() || null;
      payload.postal_code = postalCode.trim();
      payload.save_address_to_profile = saveAddressToProfile;
      payload.address_id = selectedAddressId || null;
      payload.post_office_id = null;
    } else {
      payload.post_office_id = selectedPostOfficeId;
      payload.save_address_to_profile = false;
      payload.address_id = null;
    }

    checkoutMutation.mutate(payload);
  };

  if (isProfileLoading || isCartLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ПОДГОТОВКА ОФОРМЛЕНИЯ ЗАКАЗА... )
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex flex-col items-center justify-center py-20 px-4 text-center">
        <div className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          КОРЗИНА ПУСТА
        </div>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-md">
          Для оформления заказа добавьте хотя бы один товар в корзину.
        </p>
        <Link
          to="/catalog"
          className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-8 py-3 text-xs font-sans uppercase tracking-wider transition-colors rounded-none"
        >
          ПЕРЕЙТИ В КАТАЛОГ ↗
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#F2E9DB] min-h-screen py-10 md:py-16">
      <div className="w-full max-w-none px-4 md:px-8 space-y-8">
        {/* Header */}
        <div className="border-b border-[#3F2021]/20 pb-6">
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
            ( ЭТАП ОФОРМЛЕНИЯ )
          </span>
          <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#3F2021] mt-1">
            ОФОРМЛЕНИЕ ЗАКАЗА
          </h1>
        </div>

        {checkoutError && (
          <div className="p-4 bg-red-100 text-red-900 border border-red-300 text-xs font-sans rounded-none">
            {checkoutError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Form Sections */}
          <div className="lg:col-span-8 space-y-8">
            {/* 1. Recipient Info Section */}
            <section className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-8 rounded-none space-y-5">
              <div className="border-b border-[#3F2021]/15 pb-3">
                <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block mb-1">
                  ( 1 / 3 )
                </span>
                <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  ДАННЫЕ ПОЛУЧАТЕЛЯ
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                    ИМЯ *
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={100}
                    placeholder="Иван"
                    value={recipientFirstname}
                    onChange={(e) => setRecipientFirstname(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                    ФАМИЛИЯ *
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={100}
                    placeholder="Иванов"
                    value={recipientLastname}
                    onChange={(e) => setRecipientLastname(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                    ОТЧЕСТВО
                  </label>
                  <input
                    type="text"
                    maxLength={100}
                    placeholder="Иванович"
                    value={recipientMiddlename}
                    onChange={(e) => setRecipientMiddlename(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-[#3F2021]/10">
                <input
                  type="checkbox"
                  id="saveToProfile"
                  checked={saveToProfile}
                  onChange={(e) => setSaveToProfile(e.target.checked)}
                  className="w-4 h-4 rounded-none accent-[#3F2021] cursor-pointer"
                />
                <label
                  htmlFor="saveToProfile"
                  className="text-xs font-sans uppercase tracking-wider text-[#3F2021] cursor-pointer font-semibold select-none"
                >
                  СОХРАНИТЬ В ПРОФИЛЬ
                </label>
              </div>
            </section>

            {/* 2. Passport Data Section */}
            <section className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-8 rounded-none space-y-5">
              <div className="border-b border-[#3F2021]/15 pb-3">
                <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block mb-1">
                  ( 2 / 3 )
                </span>
                <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  ПАСПОРТНЫЕ ДАННЫЕ (ДЛЯ ТАМОЖЕННОГО/ПОЧТОВОГО ОФОРМЛЕНИЯ)
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                    СЕРИЯ (4 ЦИФРЫ) *
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={4}
                    placeholder="1234"
                    value={passportSeries}
                    onChange={(e) => {
                      const clean = e.target.value.replace(/\D/g, '').slice(0, 4);
                      setPassportSeries(clean);
                    }}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-mono outline-none rounded-none text-[#3F2021]"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                    НОМЕР (6 ЦИФР) *
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    placeholder="567890"
                    value={passportNumber}
                    onChange={(e) => {
                      const clean = e.target.value.replace(/\D/g, '').slice(0, 6);
                      setPassportNumber(clean);
                    }}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-mono outline-none rounded-none text-[#3F2021]"
                  />
                </div>
              </div>

              <div className="p-3 bg-[#F2E9DB]/60 border border-[#3F2021]/15 text-[11px] font-sans uppercase tracking-wide text-[#3F2021]/80 leading-relaxed">
                ПАСПОРТНЫЕ ДАННЫЕ СОХРАНЯЮТСЯ ТОЛЬКО В ДАННОМ ЗАКАЗЕ И УДАЛЯЮТСЯ ПОСЛЕ ПОЛУЧЕНИЯ ИЛИ ВОЗВРАТА ПОСЫЛКИ
              </div>
            </section>

            {/* 3. Delivery Section (Address or Post Office) */}
            <section className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-8 rounded-none space-y-6">
              <div className="border-b border-[#3F2021]/15 pb-3">
                <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block mb-1">
                  ( 3 / 3 )
                </span>
                <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  СПОСОБ ДОСТАВКИ
                </h2>
              </div>

              {/* Mode Switcher Toggle */}
              <div className="grid grid-cols-2 border border-[#3F2021]">
                <button
                  type="button"
                  onClick={() => setDeliveryMode('address')}
                  className={`py-3 text-xs font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none text-center ${
                    deliveryMode === 'address'
                      ? 'bg-[#3F2021] text-[#F2E9DB]'
                      : 'bg-[#FFFFFF] text-[#3F2021] hover:bg-[#F2E9DB]/50'
                  }`}
                >
                  ДОСТАВКА ПО АДРЕСУ
                </button>
                <button
                  type="button"
                  onClick={() => setDeliveryMode('post_office')}
                  className={`py-3 text-xs font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none text-center border-l border-[#3F2021] ${
                    deliveryMode === 'post_office'
                      ? 'bg-[#3F2021] text-[#F2E9DB]'
                      : 'bg-[#FFFFFF] text-[#3F2021] hover:bg-[#F2E9DB]/50'
                  }`}
                >
                  ВЫБРАТЬ ПОЧТУ
                </button>
              </div>

              {/* MODE A: Address Delivery */}
              {deliveryMode === 'address' ? (
                <div className="space-y-6">
                  {/* Saved Addresses Cards */}
                  {addresses.length > 0 && (
                    <div className="space-y-2">
                      <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 font-semibold">
                        СОХРАНЁННЫЕ АДРЕСА:
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {addresses.map((addr) => {
                          const isSelected = selectedAddressId === addr.id;
                          return (
                            <button
                              key={addr.id}
                              type="button"
                              onClick={() => handleSelectSavedAddress(addr)}
                              className={`p-3 text-left border rounded-none transition-colors cursor-pointer ${
                                isSelected
                                  ? 'border-[#3F2021] bg-[#3F2021] text-[#F2E9DB]'
                                  : 'border-[#3F2021]/30 bg-[#FFFFFF] hover:border-[#3F2021] text-[#3F2021]'
                              }`}
                            >
                              <div className="text-xs font-sans font-bold uppercase truncate">
                                Г. {addr.city}, {addr.house || addr.street || ''}
                                {addr.apartment ? `, КВ. ${addr.apartment}` : ''}
                              </div>
                              <div className={`text-[10px] font-mono mt-1 ${isSelected ? 'text-[#F2E9DB]/80' : 'text-[#3F2021]/60'}`}>
                                ИНДЕКС: {addr.postal_code} {addr.is_default ? '· ПО УМОЛЧАНИЮ' : ''}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Separated Address Fields */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
                    <div>
                      <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                        СТРАНА *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="Россия"
                        value={country}
                        onChange={(e) => {
                          setSelectedAddressId(null);
                          setCountry(e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                        ОБЛАСТЬ / РЕГИОН
                      </label>
                      <input
                        type="text"
                        placeholder="Московская область"
                        value={region}
                        onChange={(e) => {
                          setSelectedAddressId(null);
                          setRegion(e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                        ГОРОД *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="Москва"
                        value={city}
                        onChange={(e) => {
                          setSelectedAddressId(null);
                          setCity(e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                        ДОМ / УЛИЦА *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="ул. Тверская, д. 1"
                        value={house}
                        onChange={(e) => {
                          setSelectedAddressId(null);
                          setHouse(e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                        КВАРТИРА
                      </label>
                      <input
                        type="text"
                        placeholder="кв. 10"
                        value={apartment}
                        onChange={(e) => {
                          setSelectedAddressId(null);
                          setApartment(e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                        ПОСТ-КОД (ИНДЕКС) *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="101000"
                        value={postalCode}
                        onChange={(e) => {
                          setSelectedAddressId(null);
                          setPostalCode(e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-mono outline-none rounded-none text-[#3F2021]"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-[#3F2021]/10">
                    <input
                      type="checkbox"
                      id="saveAddressToProfile"
                      checked={saveAddressToProfile}
                      onChange={(e) => setSaveAddressToProfile(e.target.checked)}
                      className="w-4 h-4 rounded-none accent-[#3F2021] cursor-pointer"
                    />
                    <label
                      htmlFor="saveAddressToProfile"
                      className="text-xs font-sans uppercase tracking-wider text-[#3F2021] cursor-pointer font-semibold select-none"
                    >
                      СОХРАНИТЬ НОВЫЙ АДРЕС В ПРОФИЛЬ
                    </label>
                  </div>
                </div>
              ) : (
                /* MODE B: Post Office Delivery */
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                      ПОИСК ОТДЕЛЕНИЯ ПО ГОРОДУ ИЛИ НАЗВАНИЮ:
                    </label>
                    <input
                      type="text"
                      placeholder="Введите город или номер отделения (например: Екатеринбург, 620000)..."
                      value={postOfficeSearch}
                      onChange={(e) => setPostOfficeSearch(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                    />
                  </div>

                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {isPostOfficesLoading ? (
                      <div className="p-6 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                        ( ПОИСК ОТДЕЛЕНИЙ... )
                      </div>
                    ) : postOffices.length === 0 ? (
                      <div className="p-6 text-center border border-[#3F2021]/20 bg-[#F2E9DB]/30 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
                        ( ОТДЕЛЕНИЯ НЕ НАЙДЕНЫ )
                      </div>
                    ) : (
                      postOffices.map((po: PostOfficeResponse) => {
                        const isSelected = selectedPostOfficeId === po.id;
                        return (
                          <button
                            key={po.id}
                            type="button"
                            onClick={() => setSelectedPostOfficeId(po.id)}
                            className={`w-full text-left p-3.5 border rounded-none transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                              isSelected
                                ? 'border-[#3F2021] bg-[#3F2021] text-[#F2E9DB]'
                                : 'border-[#3F2021]/25 bg-[#FFFFFF] hover:border-[#3F2021] text-[#3F2021]'
                            }`}
                          >
                            <div className="space-y-1">
                              <div className="font-serif text-sm font-bold uppercase tracking-wide">
                                {po.name}
                              </div>
                              <div className={`text-xs font-sans ${isSelected ? 'text-[#F2E9DB]/90' : 'text-[#3F2021]/80'}`}>
                                Г. {po.city}, {po.house} {po.region ? `(${po.region})` : ''}
                              </div>
                              {po.note && (
                                <div className={`text-[10px] font-sans ${isSelected ? 'text-[#F2E9DB]/70' : 'text-[#3F2021]/60'}`}>
                                  {po.note}
                                </div>
                              )}
                            </div>

                            <div className="font-mono text-xs font-bold shrink-0">
                              ИНДЕКС: {po.postal_code} {isSelected ? '✓' : ''}
                            </div>
                          </button>
                        );
                      })
                    )}
                  </div>
                </div>
              )}

              {/* Optional Comment */}
              <div className="pt-2 border-t border-[#3F2021]/15">
                <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                  КОММЕНТАРИЙ К ЗАКАЗУ (НЕОБЯЗАТЕЛЬНО)
                </label>
                <input
                  type="text"
                  maxLength={500}
                  placeholder="Код домофона, удобное время звонка..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                />
              </div>
            </section>
          </div>

          {/* Right Column: Order Summary & Checkout Button */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 rounded-none space-y-6 sticky top-24">
              <div className="border-b border-[#3F2021]/15 pb-3">
                <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block mb-1">
                  ( ВАШ ЗАКАЗ )
                </span>
                <h3 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  ИТОГО К ОПЛАТЕ
                </h3>
              </div>

              {/* Items List in Summary */}
              <div className="space-y-3 max-h-60 overflow-y-auto divide-y divide-[#3F2021]/10">
                {items.map((item) => (
                  <div key={item.id} className="pt-2 first:pt-0 flex items-start justify-between gap-3 text-xs font-sans">
                    <div>
                      <div className="font-serif font-semibold text-[#3F2021] uppercase">
                        {item.title}
                      </div>
                      <div className="text-[10px] text-[#3F2021]/60 uppercase">
                        {item.color_name} {item.size ? `/ РАЗМЕР: ${item.size}` : ''} × {item.quantity} шт.
                      </div>
                    </div>
                    <span className="font-mono font-bold text-[#3F2021] whitespace-nowrap">
                      {formatPrice(item.total_price)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-[#3F2021]/20 space-y-2">
                <div className="flex justify-between items-baseline text-xs font-sans text-[#3F2021]/70 uppercase">
                  <span>ТОВАРОВ В КОРЗИНЕ:</span>
                  <span>{items.reduce((s, i) => s + i.quantity, 0)} шт.</span>
                </div>
                <div className="flex justify-between items-baseline text-xs font-sans text-[#3F2021]/70 uppercase">
                  <span>ДОСТАВКА:</span>
                  <span>РАССЧИТЫВАЕТСЯ</span>
                </div>
                <div className="flex justify-between items-baseline pt-2 border-t border-[#3F2021]/15 text-[#3F2021]">
                  <span className="font-sans font-bold text-xs uppercase tracking-wider">ИТОГО:</span>
                  <span className="font-serif text-2xl font-bold">
                    {formatPrice(totalAmount)}
                  </span>
                </div>
              </div>

              <button
                type="submit"
                disabled={checkoutMutation.isPending}
                className="w-full bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] py-3.5 text-xs font-sans font-semibold uppercase tracking-widest transition-colors cursor-pointer rounded-none disabled:opacity-50"
              >
                {checkoutMutation.isPending ? 'ОФОРМЛЕНИЕ...' : 'ПЕРЕЙТИ К ОПЛАТЕ ↗'}
              </button>

              <div className="text-[10px] font-sans text-[#3F2021]/60 text-center uppercase tracking-wider">
                НАЖИМАЯ «ПЕРЕЙТИ К ОПЛАТЕ», ВЫ ПОДТВЕРЖДАЕТЕ СОГЛАСИЕ С УСЛОВИЯМИ СЕРВИСА
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CheckoutPage;
