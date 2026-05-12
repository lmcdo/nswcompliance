'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Shield, MapPin, Clock, Eye } from 'lucide-react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

export function HomeHero() {
  const [address, setAddress] = useState('');
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (address.trim()) {
      router.push(`/property?address=${encodeURIComponent(address.trim())}`);
    }
  };

  return (
    <section id="hero-search" className="px-6 pt-20 pb-16 max-w-3xl mx-auto text-center">
      <div className="mb-6 flex justify-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-4 py-1.5 text-sm font-medium text-teal-700">
          <span className="w-2 h-2 rounded-full bg-teal-500" />
          Seven free checks for any NSW address
        </div>
      </div>

      <h1 className="text-4xl sm:text-5xl font-bold leading-tight text-gray-900 mb-4">
        What should you know{' '}
        <span className="text-teal-600">before you buy, build, or insure?</span>
      </h1>

      <p className="text-gray-500 text-lg mb-8 max-w-xl mx-auto">
        Live government data, satellite imagery, and Bureau of Meteorology records. No account needed.
      </p>

      <form onSubmit={handleSubmit} className="relative mx-auto max-w-2xl">
        <div className="relative flex items-center rounded-2xl bg-white shadow-xl ring-1 ring-gray-200 transition-all duration-300 focus-within:ring-teal-500 focus-within:shadow-teal-500/10 focus-within:shadow-2xl">
          <div className="flex items-center pl-5">
            <MapPin className="h-5 w-5 text-gray-400" />
          </div>

          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={(addr) => setAddress(addr)}
            placeholder="Enter any NSW property address..."
            className="flex-1 bg-transparent px-4 py-5 text-lg text-gray-900 placeholder:text-gray-400 focus:outline-none"
          />

          <div className="pr-2">
            <button
              type="submit"
              disabled={!address.trim()}
              className="flex items-center gap-2 rounded-xl px-6 py-3 bg-teal-600 text-white text-sm font-semibold hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Search className="h-4 w-4" />
              Check property
            </button>
          </div>
        </div>

        <div className="mt-4 flex justify-center gap-6 text-sm text-gray-400">
          <span className="flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5" />
            Data never stored
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            Results in 8 seconds
          </span>
          <span className="flex items-center gap-1.5">
            <Eye className="h-3.5 w-3.5" />
            Free preview included
          </span>
        </div>
      </form>
    </section>
  );
}
