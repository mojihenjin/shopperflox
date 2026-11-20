import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';

function PageFallback() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-8 h-8 border-2 border-sf-dark/20 border-t-sf-dark rounded-full animate-spin" />
    </div>
  );
}

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-[#F2E9DB] text-sf-black font-sans selection:bg-sf-dark selection:text-sf-cream">
      <Header />
      <main className="flex-1">
        <Suspense fallback={<PageFallback />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}
