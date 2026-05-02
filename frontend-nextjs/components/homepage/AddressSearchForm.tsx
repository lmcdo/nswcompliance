'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

const PLACEHOLDER_ADDRESSES = [
  '14 Rosebery Ave, Rosebery NSW 2018',
  '38 Cabarita Rd, Concord NSW 2137',
  '5 Griffith St, Balmain NSW 2041',
  '22 Livingstone Rd, Marrickville NSW 2204',
  '101 Terry Rd, Eastwood NSW 2122',
];

export function AddressSearchForm() {
  const router = useRouter();
  const [address, setAddress] = useState('');
  const [placeholder, setPlaceholder] = useState(PLACEHOLDER_ADDRESSES[0]);
  const idxRef = useRef(0);

  useEffect(() => {
    const id = setInterval(() => {
      idxRef.current = (idxRef.current + 1) % PLACEHOLDER_ADDRESSES.length;
      setPlaceholder(PLACEHOLDER_ADDRESSES[idxRef.current]);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!address.trim()) return;
    router.push(`/granny-flat?address=${encodeURIComponent(address.trim())}`);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 max-w-xl mx-auto">
      <input
        type="text"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        placeholder={placeholder}
        className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-[#00d9b8] focus:border-transparent transition-all"
      />
      <button
        type="submit"
        className="px-5 py-3 bg-[#00d9b8] text-[#0b1628] font-semibold text-sm rounded-xl hover:bg-[#00c4a7] transition-colors whitespace-nowrap"
      >
        Check →
      </button>
    </form>
  );
}
