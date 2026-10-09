'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV_LINKS = [
  { label: 'Overview', path: '/' },
  { label: 'How It Works', path: '/pipeline' },
  { label: 'Ask NutriKid', path: '/ask' },
  { label: 'Institutional Sources', path: '/sources' },
  { label: 'Retrieval Lab', path: '/retrieval-lab' },
  { label: 'Evaluation & Benchmarks', path: '/evaluation' },
  { label: 'Safety & Scope', path: '/safety' },
];

export default function Navbar() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [menuOpen, setMenuOpen] = useState(false);

  // Initialize theme from localStorage / system preference
  useEffect(() => {
    const saved = localStorage.getItem('nk-theme') as 'dark' | 'light' | null;
    const preferred = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    const initial = saved ?? preferred;
    setTheme(initial);
    applyTheme(initial);
  }, []);

  const applyTheme = (t: 'dark' | 'light') => {
    document.documentElement.classList.remove('dark', 'light');
    document.documentElement.classList.add(t);
  };

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    applyTheme(next);
    localStorage.setItem('nk-theme', next);
  };

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        backgroundColor: 'var(--header-bg)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--header-border)',
        transition: 'background-color 0.2s ease, border-color 0.2s ease',
      }}
    >
      <div
        style={{
          maxWidth: 1800,
          margin: '0 auto',
          padding: '0 24px',
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        {/* Logo + Clinical Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0 }}>
          <Link
            href="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              textDecoration: 'none',
              transition: 'opacity 0.15s ease',
            }}
          >
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 8,
                backgroundColor: 'var(--surface-container-high)',
                border: '1px solid var(--border-highlight)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)',
              }}
            >
              <span className="material-symbols-outlined text-primary" style={{ fontSize: 19 }}>
                vital_signs
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span
                className="font-geist"
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  color: 'var(--on-surface)',
                  letterSpacing: '-0.02em',
                  lineHeight: 1.2,
                }}
              >
                Nutri<span style={{ color: 'var(--primary-container)' }}>Kid</span>
              </span>
            </div>
          </Link>

          {/* Refined Clinical Badge */}
          <div className="hidden-mobile" style={{ display: 'flex', alignItems: 'center' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 9px',
                borderRadius: 6,
                fontSize: 11,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                letterSpacing: '0.01em',
                backgroundColor: 'rgba(2, 132, 199, 0.08)',
                color: 'var(--secondary)',
                border: '1px solid rgba(2, 132, 199, 0.22)',
              }}
            >
              <span
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  backgroundColor: 'var(--secondary)',
                  display: 'inline-block',
                }}
              />
              Pediatric Nutrition RAG
            </span>
          </div>
        </div>

        {/* Desktop Nav */}
        <nav
          style={{ display: 'flex', alignItems: 'center', gap: 4 }}
          className="desktop-nav"
        >
          {NAV_LINKS.map((link) => (
            <Link
              key={link.path}
              href={link.path}
              className={`nav-link ${pathname === link.path ? 'active' : ''}`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          {/* Scope indicator */}
          <div
            className="navbar-scope-badge"
            title="Clinical Safety Guard: Strict cohort boundary 5.0 to 15.0 years"
          >
            <span className="navbar-scope-pulse" />
            <span className="navbar-scope-text">SCOPE: 5.0–15.0 YRS</span>
          </div>

          {/* Evidence Grounded Status Pill */}
          <div
            className="hidden-tablet"
            title="Institutional Sources: WHO, ICMR-NIN 2020/2024 & FAO Guidelines"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              padding: '4px 10px',
              borderRadius: 20,
              backgroundColor: 'var(--surface-container-high)',
              border: '1px solid var(--border-subtle)',
              fontSize: 11,
              fontFamily: 'Inter, sans-serif',
              fontWeight: 500,
              color: 'var(--on-surface-variant)',
              userSelect: 'none',
            }}
          >
            <span
              className="material-symbols-outlined text-primary"
              style={{ fontSize: 14 }}
            >
              verified
            </span>
            <span>Evidence-Grounded</span>
          </div>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            className="navbar-theme-btn"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--on-surface)' }}>
              {theme === 'dark' ? 'light_mode' : 'dark_mode'}
            </span>
          </button>

          {/* Mobile menu toggle */}
          <button
            className="mobile-menu-btn"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle navigation"
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              backgroundColor: 'var(--surface-container-high)',
              border: '1px solid var(--border-subtle)',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--on-surface)' }}>
              {menuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div
          style={{
            backgroundColor: 'var(--surface-raised)',
            borderTop: '1px solid var(--border-subtle)',
            padding: '12px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
            boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
          }}
          className="mobile-menu"
        >
          {NAV_LINKS.map((link) => (
            <Link
              key={link.path}
              href={link.path}
              className={`nav-link ${pathname === link.path ? 'active' : ''}`}
              onClick={() => setMenuOpen(false)}
              style={{ display: 'block' }}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
