import React, { useState } from 'react';
import { Sparkles, ArrowRight, PenTool, FileText, Download } from 'lucide-react';

export default function LandingPage({ onNavigate, user }) {
  const [sandboxText, setSandboxText] = useState("Type here to watch this translate to handwritten script in real-time. Change inks and backings to see the bleed and layout change!");
  const [sandboxFont, setSandboxFont] = useState("Caveat");
  const [sandboxColor, setSandboxColor] = useState("ink-blue");
  const [sandboxPaper, setSandboxPaper] = useState("paper-lined");

  const fonts = [
    { name: 'Playful Cursive', value: 'Caveat' },
    { name: 'Real Handwriting', value: 'Homemade Apple' },
    { name: 'Elegant Calligraphy', value: 'Sacramento' },
    { name: 'Neat Print', value: 'Patrick Hand' },
    { name: 'Informal Sketch', value: 'Reenie Beanie' }
  ];

  const colors = [
    { name: 'Royal Blue', class: 'ink-blue', color: '#1e3a80' },
    { name: 'Classic Black', class: 'ink-black', color: '#212529' },
    { name: 'Deep Red', class: 'ink-red', color: '#922b2b' },
    { name: 'Forest Green', class: 'ink-green', color: '#1b4d3e' }
  ];

  const papers = [
    { name: 'Lined Notebook', value: 'paper-lined' },
    { name: 'Graph Grid', value: 'paper-grid' },
    { name: 'Clean Parchment', value: 'paper-plain' }
  ];

  return (
    <div className="relative min-h-screen overflow-hidden" id="landing-page">
      {/* Dynamic Pastel Animated Background */}
      <div className="pastel-bg-grid"></div>

      {/* Navigation Header */}
      <header className="flex justify-between items-center px-8 py-8 max-w-7xl mx-auto z-10 relative">
        <div className="flex items-center gap-2 font-extrabold text-2xl tracking-tight text-[var(--text-main)]" style={{ fontStyle: 'italic' }}>
          <span className="p-2.5 bg-white rounded-xl flex items-center justify-center shadow-sm border border-slate-200/40 animate-float">
            <PenTool size={24} className="text-[var(--periwinkle-glow)]" />
          </span>
          Scribble<span className="text-[var(--periwinkle-glow)]">AI</span>
        </div>
        <div className="flex items-center gap-4">
          {user ? (
            <button
              onClick={() => onNavigate('workspace')}
              className="btn-primary"
              id="header-workspace-btn"
            >
              Go to Workspace
              <ArrowRight size={16} />
            </button>
          ) : (
            <>
              <button
                onClick={() => onNavigate('auth')}
                className="px-6 py-2.5 rounded-full text-sm font-bold text-[var(--text-main)] hover:bg-white/40 transition-all duration-300"
                id="header-login-btn"
              >
                Log In
              </button>
              <button
                onClick={() => onNavigate('auth')}
                className="btn-primary"
                id="header-signup-btn"
              >
                Get Started Free
              </button>
            </>
          )}
        </div>
      </header>

      {/* Hero Section - Increased Breathing Room */}
      <main className="max-w-7xl mx-auto px-8 pt-16 pb-28 grid grid-cols-1 lg:grid-cols-12 gap-24 lg:gap-28 items-center z-5 relative">
        
        {/* Hero Details - Spacing expanded */}
        <div className="lg:col-span-5 flex flex-col gap-8 text-left">
          <div className="inline-flex items-center gap-2 px-4.5 py-1.5 rounded-full bg-[var(--periwinkle-light)] border border-[var(--periwinkle-dark)]/40 text-xs font-extrabold text-[var(--periwinkle-glow-hover)] w-fit shadow-sm uppercase tracking-wider">
            <Sparkles size={12} className="text-[var(--periwinkle-glow)] animate-pulse" />
            AI Document Handwriting Synthesis
          </div>
          
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-[var(--text-main)] leading-tight">
            Realistic <span className="glow-text-primary">Handwriting</span> at your fingertips.
          </h1>
          
          <p className="text-md text-[var(--text-muted)] max-w-xl leading-relaxed">
            ScribbleAI merges synthetic text compilation with physical cursive rendering. Upload documents, prompts, or notes, and render authentic physical outputs instantly.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mt-2">
            <button
              onClick={() => onNavigate(user ? 'workspace' : 'auth')}
              className="btn-primary"
              id="hero-primary-btn"
            >
              Start Generating Free
              <ArrowRight size={18} />
            </button>
            <a
              href="#sandbox"
              className="btn-secondary"
            >
              Try the Sandbox
            </a>
          </div>

          {/* Quick trust metrics - Expanded spacing */}
          <div className="flex gap-8 mt-10 pt-8 border-t border-slate-200/40">
            <div>
              <div className="text-2xl font-black text-[var(--text-main)]">6+</div>
              <div className="text-xs font-bold text-[var(--text-muted)]">Real Cursive Fonts</div>
            </div>
            <div>
              <div className="text-2xl font-black text-[var(--text-main)]">100%</div>
              <div className="text-xs font-bold text-[var(--text-muted)]">Print Ready A4 PDF</div>
            </div>
            <div>
              <div className="text-2xl font-black text-[var(--text-main)]">Secure</div>
              <div className="text-xs font-bold text-[var(--text-muted)]">Supabase Sync</div>
            </div>
          </div>
        </div>

        {/* Hero Interactive Playground (Live Sandbox) */}
        <div className="lg:col-span-7 lg:pl-8" id="sandbox">
          <div className="glass-panel p-8 md:p-10 flex flex-col gap-8 relative shadow-lg bg-white/70 border-white/80">
            
            {/* Visual Header */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider text-[var(--text-light)] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[var(--periwinkle-glow)] animate-ping"></span>
                Live Sandbox Explorer
              </span>
              <div className="flex gap-1.5">
                <span className="w-3.5 h-3.5 rounded-full bg-[var(--periwinkle-light)] border border-slate-200/20 shadow-sm"></span>
                <span className="w-3.5 h-3.5 rounded-full bg-[var(--butter-light)] border border-slate-200/20 shadow-sm"></span>
                <span className="w-3.5 h-3.5 rounded-full bg-[var(--periwinkle)] border border-slate-200/20 shadow-sm"></span>
              </div>
            </div>

            {/* Simulated Paper Canvas with Spiral Binder rings - Increased Padding */}
            <div className={`w-full min-h-[360px] p-10 md:p-12 rounded-lg relative overflow-hidden transition-all duration-300 ${sandboxPaper}`}>
              
              {/* Binder Spiral Rings */}
              {(sandboxPaper === 'paper-lined' || sandboxPaper === 'paper-grid') && (
                <div className="absolute left-[12px] top-6 bottom-6 w-[25px] flex flex-col justify-between pointer-events-none select-none z-10" style={{ opacity: 0.85 }}>
                  {Array.from({ length: 11 }).map((_, idx) => (
                    <div key={idx} className="flex items-center gap-1 h-6">
                      <div className="w-2.5 h-2.5 rounded-full bg-slate-300 shadow-inner border border-slate-400/20"></div>
                      <div className="w-7 h-2 rounded-full bg-gradient-to-b from-slate-400 via-slate-100 to-slate-400 shadow-sm border border-slate-400/25 transform rotate-[18deg] -translate-y-0.5"></div>
                    </div>
                  ))}
                </div>
              )}

              {/* Ink bleed SVG filter */}
              <svg className="hidden">
                <defs>
                  <filter id="inkbleed-sb">
                    <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" result="noise" />
                    <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.2" xChannelSelector="R" yChannelSelector="G" />
                  </filter>
                </defs>
              </svg>

              <div 
                className={`w-full h-full outline-none font-medium whitespace-pre-wrap select-none leading-[28px] break-words ${sandboxColor}`}
                style={{
                  fontFamily: sandboxFont,
                  fontSize: sandboxFont === 'Reenie Beanie' ? '30px' : sandboxFont === 'Homemade Apple' ? '18px' : '22px',
                  letterSpacing: '0.5px',
                  transform: 'rotate(-0.5deg)',
                  transformOrigin: 'top left',
                  paddingLeft: sandboxPaper === 'paper-plain' ? '20px' : '95px',
                  paddingTop: '5px',
                  filter: 'url(#inkbleed-sb)',
                }}
              >
                {sandboxText || "Start typing in the control box below to see it live..."}
              </div>
            </div>

            {/* Sandbox Controls Card - Increased Padding */}
            <div className="flex flex-col gap-6 bg-white/50 p-6 md:p-8 rounded-2xl border border-slate-200/40">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                
                {/* Font Selector */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-black uppercase text-[var(--text-muted)] text-left">Writing Style</label>
                  <select 
                    value={sandboxFont} 
                    onChange={(e) => setSandboxFont(e.target.value)}
                    className="p-3 rounded-xl bg-white border border-slate-200/60 text-xs text-[var(--text-main)] focus:outline-none focus:border-[var(--periwinkle-glow)]"
                    id="sandbox-font-select"
                  >
                    {fonts.map(font => (
                      <option key={font.value} value={font.value}>{font.name}</option>
                    ))}
                  </select>
                </div>

                {/* Ink Color Selector */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-black uppercase text-[var(--text-muted)] text-left">Ink Shade</label>
                  <div className="flex gap-2.5 py-1 justify-start">
                    {colors.map(color => (
                      <button
                        key={color.class}
                        onClick={() => setSandboxColor(color.class)}
                        className={`w-7 h-7 rounded-full border-2 transition-all ${sandboxColor === color.class ? 'border-[var(--periwinkle-glow)] scale-110 shadow-md' : 'border-transparent hover:scale-105'}`}
                        style={{ backgroundColor: color.color }}
                        title={color.name}
                        id={`ink-color-${color.class}`}
                      />
                    ))}
                  </div>
                </div>

                {/* Paper Template Selector */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-black uppercase text-[var(--text-muted)] text-left">Paper Canvas</label>
                  <select 
                    value={sandboxPaper} 
                    onChange={(e) => setSandboxPaper(e.target.value)}
                    className="p-3 rounded-xl bg-white border border-slate-200/60 text-xs text-[var(--text-main)] focus:outline-none focus:border-[var(--periwinkle-glow)]"
                    id="sandbox-paper-select"
                  >
                    {papers.map(paper => (
                      <option key={paper.value} value={paper.value}>{paper.name}</option>
                    ))}
                  </select>
                </div>

              </div>

              {/* Text Input */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-black uppercase text-[var(--text-muted)] text-left">Playground Input</label>
                <textarea
                  value={sandboxText}
                  onChange={(e) => setSandboxText(e.target.value)}
                  className="w-full p-4 rounded-xl bg-white border border-slate-200/60 text-xs text-[var(--text-main)] focus:outline-none focus:border-[var(--periwinkle-glow)] resize-none h-20 transition-all focus:bg-white"
                  placeholder="Enter text..."
                  id="sandbox-textarea-input"
                />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Features Overview - Increased Top/Bottom Padding & Spacing */}
      <section className="bg-white/40 py-32 md:py-36 border-t border-slate-200/30">
        <div className="max-w-7xl mx-auto px-8 flex flex-col gap-20">
          <div className="text-center flex flex-col gap-3 items-center">
            <h2 className="text-3xl md:text-4xl font-extrabold text-[var(--text-main)]">Crafted with Aesthetic Intention</h2>
            <p className="text-md text-[var(--text-muted)] max-w-xl">Every spacing margin, pen bleed stroke, and page background shade is formulated to look authentic.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="glass-panel p-8 flex flex-col gap-5 text-left hover:-translate-y-2 transition-all duration-300 bg-white/60">
              <div className="w-12 h-12 rounded-2xl bg-[var(--periwinkle-light)] flex items-center justify-center text-[var(--periwinkle-glow)] shadow-sm">
                <FileText size={22} />
              </div>
              <h3 className="text-lg font-extrabold text-[var(--text-main)]">Document Text Extraction</h3>
              <p className="text-[var(--text-muted)] text-xs leading-relaxed">Drag and drop plain text files to extract and parse documents instantly. No manual typing or configuration required.</p>
            </div>

            <div className="glass-panel p-8 flex flex-col gap-5 text-left hover:-translate-y-2 transition-all duration-300 bg-white/60">
              <div className="w-12 h-12 rounded-2xl bg-[var(--butter-light)] flex items-center justify-center text-[var(--yellow-glow)] shadow-sm">
                <Sparkles size={22} />
              </div>
              <h3 className="text-lg font-extrabold text-[var(--text-main)]">AI Composition Companion</h3>
              <p className="text-[var(--text-muted)] text-xs leading-relaxed">Instantly request drafts from the AI helper chat for letters, summaries, thank-you notes, or quick apology drafts.</p>
            </div>

            <div className="glass-panel p-8 flex flex-col gap-5 text-left hover:-translate-y-2 transition-all duration-300 bg-white/60">
              <div className="w-12 h-12 rounded-2xl bg-[var(--periwinkle-light)] flex items-center justify-center text-[var(--periwinkle-glow-hover)] shadow-sm">
                <Download size={22} />
              </div>
              <h3 className="text-lg font-extrabold text-[var(--text-main)]">Vector PDF Exports</h3>
              <p className="text-[var(--text-muted)] text-xs leading-relaxed">Save your documents as high-fidelity vectors. Ready to print, scan, or download for digital sharing.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 text-center text-xs text-[var(--text-light)] border-t border-slate-200/20 z-5 relative bg-white/20">
        <p>&copy; 2026 ScribbleAI. Handcrafted with Supabase integration. All rights reserved.</p>
      </footer>
    </div>
  );
}
