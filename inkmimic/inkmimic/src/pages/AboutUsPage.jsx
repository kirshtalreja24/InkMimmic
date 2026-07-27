import { Link } from 'react-router-dom';
import { Navbar } from '../components/layout/Navbar.jsx';
import { Footer } from '../components/layout/Footer.jsx';
import { Card } from '../components/ui/Card.jsx';
import { Button } from '../components/ui/Button.jsx';

export default function AboutUsPage() {
  return (
    <div className="min-h-screen bg-ink-950 bg-ink-grain">
      <Navbar />

      <main className="mx-auto max-w-4xl px-6 py-20 md:px-10">
        <p className="font-script text-xl text-royal-400">about us</p>
        <h1 className="mt-3 font-display text-4xl text-parchment md:text-5xl">
          We think handwriting is worth keeping.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-parchment/60">
          Inkmimic started from a simple annoyance: typing feels efficient, but it flattens
          everything to the same font. A note to yourself looks identical to a note to your bank.
          We wanted a way to keep the personal shape of handwriting without redoing the actual
          writing by hand every time.
        </p>

        <div className="mt-14 grid gap-6 md:grid-cols-2">
          <Card>
            <h2 className="font-display text-xl text-parchment">What we build</h2>
            <p className="mt-3 text-sm leading-relaxed text-parchment/55">
              A workspace where you upload one sample of your handwriting, describe what you need,
              and get back a new page — regenerated in that same hand. Cleaner drafts, longer
              versions, or a steadier line on a day your hand isn't cooperating.
            </p>
          </Card>
          <Card>
            <h2 className="font-display text-xl text-parchment">What we don't do</h2>
            <p className="mt-3 text-sm leading-relaxed text-parchment/55">
              We don't store your samples anywhere you can't see, and we don't use your
              handwriting for anything beyond the request you asked for. Your hand stays yours.
            </p>
          </Card>
        </div>

        <div className="mt-16 flex flex-col items-start gap-4 border-t border-royal-500/15 pt-10">
          <p className="text-parchment/50">Ready to try it with your own handwriting?</p>
          <Button as={Link} to="/auth">
            Get started
          </Button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
