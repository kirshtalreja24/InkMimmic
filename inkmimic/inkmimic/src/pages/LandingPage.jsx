import { Link } from 'react-router-dom';
import { Navbar } from '../components/layout/Navbar.jsx';
import { Footer } from '../components/layout/Footer.jsx';
import { Button } from '../components/ui/Button.jsx';
import { Card } from '../components/ui/Card.jsx';
import { InkDivider } from '../components/ui/InkDivider.jsx';
import { InkWordmark } from '../components/ui/InkWordmark.jsx';

const STEPS = [
  {
    title: 'Upload a sample',
    body: 'Drag in a photo or scan of a page you already wrote. One paragraph is enough.',
  },
  {
    title: 'Tell it what you need',
    body: 'Ask for a cleaner copy, a longer version, or the same note in a steadier hand.',
  },
  {
    title: 'Get your page back',
    body: 'Inkmimic hands back a new artifact that still looks unmistakably like your own writing.',
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-ink-950 bg-ink-grain">
      <Navbar />

      <main>
        <section className="mx-auto flex max-w-5xl flex-col items-center px-6 pb-24 pt-16 text-center md:pt-24">
          <p className="mb-6 font-script text-xl text-royal-400 animate-fade-up">
            for people who'd rather write than type
          </p>
          <h1 className="text-balance font-display text-5xl leading-[1.05] text-parchment md:text-7xl">
            <InkWordmark /> <br className="hidden md:block" />
            <span className="animate-fade-up inline-block" style={{ animationDelay: '0.15s' }}>
              turns typed words into <span className="text-gold-300">your</span> handwriting.
            </span>
          </h1>

          <p
            className="mt-8 max-w-xl text-balance text-lg text-parchment/60 animate-fade-up"
            style={{ animationDelay: '0.3s' }}
          >
            Upload one sample of how you write. Ask for what you need. Get back a page in the same
            ink, the same slant, the same hand — just tidier, longer, or different, on request.
          </p>

          <div
            className="mt-10 flex flex-col gap-4 sm:flex-row animate-fade-up"
            style={{ animationDelay: '0.45s' }}
          >
            <Button as={Link} to="/auth">
              Get started
            </Button>
            <Button as={Link} to="/about" variant="outline">
              About us
            </Button>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 pb-24 md:px-10">
          <div className="mb-10 flex items-center gap-4 text-parchment/40">
            <InkDivider />
            <span className="text-xs uppercase tracking-[0.25em]">How it works</span>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {STEPS.map((step, i) => (
              <Card key={step.title} className="relative">
                <span className="font-script text-3xl text-royal-400/70">{i + 1}</span>
                <h3 className="mt-3 font-display text-xl text-parchment">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-parchment/55">{step.body}</p>
              </Card>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-28 md:px-10">
          <div className="ink-panel flex flex-col items-center gap-6 px-8 py-14 text-center md:px-16">
            <h2 className="font-display text-3xl text-parchment md:text-4xl">
              Your handwriting, on demand.
            </h2>
            <p className="max-w-md text-parchment/55">
              No new alphabet to learn, no new tool to master — just the page you meant to write,
              whenever you need it again.
            </p>
            <Button as={Link} to="/auth">
              Start writing
            </Button>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
